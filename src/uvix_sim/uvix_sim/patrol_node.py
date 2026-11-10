#!/usr/bin/env python3
"""
Patrulla por cobertura sobre el mapa de Nav2.

Divide /map en celdas, va a la celda no visitada con ruta más corta, espera
dwell_time y repite en rondas infinitas. Incluye anti-atasco (retroceso + punto
de escape) y omite goals cercanos inalcanzables. Publica /patrol/markers.

  ros2 run Uvix_sim patrol_node --ros-args \
      --params-file ~/uvix_ws/install/Uvix_sim/share/Uvix_sim/config/patrol_params.yaml
"""

import math
import signal

import numpy as np
import rclpy
from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import Point, PoseStamped
from nav2_msgs.action import BackUp, ComputePathToPose, NavigateToPose
from nav_msgs.msg import OccupancyGrid
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
from visualization_msgs.msg import Marker, MarkerArray


def yaw_to_quat(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class PatrolNode(Node):

    def __init__(self):
        super().__init__('patrol_node')

        self.declare_parameter('global_frame', 'map')
        self.declare_parameter('robot_frame', 'base_footprint')
        self.declare_parameter('cell_size', 1.0)
        self.declare_parameter('visit_radius', 1.5)
        self.declare_parameter('min_free_ratio', 0.3)
        self.declare_parameter('max_goal_cost', 30)
        self.declare_parameter('candidates_per_try', 5)
        self.declare_parameter('max_failures', 2)
        self.declare_parameter('dwell_time', 5.0)
        self.declare_parameter('goal_timeout', 180.0)
        self.declare_parameter('exclusion_zones', [0.0])
        self.declare_parameter('exclusion_names', [''])
        self.declare_parameter('exclusion_margin', 0.5)
        self.declare_parameter('stuck_time', 5.0)
        self.declare_parameter('stuck_radius', 0.15)
        self.declare_parameter('backup_dist', 0.30)
        self.declare_parameter('backup_speed', 0.10)
        self.declare_parameter('escape_min_dist', 0.8)
        self.declare_parameter('escape_max_dist', 2.0)
        self.declare_parameter('escape_max_cost', 40)
        self.declare_parameter('escape_timeout', 25.0)
        self.declare_parameter('max_escapes', 3)
        self.declare_parameter('near_goal_dist', 2.0)
        self.declare_parameter('near_goal_timeout', 10.0)
        self.declare_parameter('near_detour_ratio', 2.0)

        gp = lambda n: self.get_parameter(n).value  # noqa: E731
        self.global_frame = gp('global_frame')
        self.robot_frame = gp('robot_frame')
        self.cell_size = float(gp('cell_size'))
        self.visit_radius = float(gp('visit_radius'))
        self.min_free_ratio = float(gp('min_free_ratio'))
        self.max_goal_cost = int(gp('max_goal_cost'))
        self.candidates_per_try = int(gp('candidates_per_try'))
        self.max_failures = int(gp('max_failures'))
        self.dwell_time = float(gp('dwell_time'))
        self.goal_timeout = float(gp('goal_timeout'))
        self.zones = self._parse_zones(gp('exclusion_zones'), gp('exclusion_names'),
                                       float(gp('exclusion_margin')))
        self.stuck_time = float(gp('stuck_time'))
        self.stuck_radius = float(gp('stuck_radius'))
        self.backup_dist = float(gp('backup_dist'))
        self.backup_speed = float(gp('backup_speed'))
        self.escape_min_dist = float(gp('escape_min_dist'))
        self.escape_max_dist = float(gp('escape_max_dist'))
        self.escape_max_cost = int(gp('escape_max_cost'))
        self.escape_timeout = float(gp('escape_timeout'))
        self.max_escapes = int(gp('max_escapes'))
        self.near_goal_dist = float(gp('near_goal_dist'))
        self.near_goal_timeout = float(gp('near_goal_timeout'))
        self.near_detour_ratio = float(gp('near_detour_ratio'))

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(OccupancyGrid, '/map', self._on_map, latched)
        self.create_subscription(OccupancyGrid, '/global_costmap/costmap', self._on_costmap, latched)
        self.marker_pub = self.create_publisher(MarkerArray, '/patrol/markers', latched)

        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.plan_client = ActionClient(self, ComputePathToPose, 'compute_path_to_pose')
        self.backup_client = ActionClient(self, BackUp, 'backup')

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.costmap = None
        self.centers = None
        self.points = []
        self.visited = None
        self.fails = None
        self.round = 1

        self.state = 'WAIT'
        self.plan_queue = []
        self.plan_results = []
        self.goal_handle = None
        self.goal_cell = None
        self.goal_xy = None
        self.nav_start = None
        self.dwell_until = None
        self.goal_seq = 0
        self.goal = None
        self.anchor = None
        self.nav_fb = None
        self.near_since = None
        self.near_recoveries = 0
        self.detour_ticks = 0
        self.escapes = 0
        self.escape_xy = None
        self.escape_deadline = None
        self.escape_history = []

        self.create_timer(0.5, self._tick)
        self.create_timer(0.5, self._update_visited)
        self.create_timer(1.0, self._publish_markers)
        self.get_logger().info(
            f'Patrulla por cobertura: celdas {self.cell_size} m, espera {self.dwell_time} s, '
            f'{len(self.zones)} zona(s) excluida(s): {", ".join(z[4] for z in self.zones) or "-"}')

    @staticmethod
    def _parse_zones(flat, names, margin):
        flat = list(flat)
        zones = []
        if len(flat) < 4:
            return zones
        for k in range(len(flat) // 4):
            xmin, ymin, xmax, ymax = flat[4 * k:4 * k + 4]
            name = names[k] if k < len(names) and names[k] else f'zona_{k}'
            zones.append((min(xmin, xmax) - margin, min(ymin, ymax) - margin,
                          max(xmin, xmax) + margin, max(ymin, ymax) + margin, name))
        return zones

    def _excluded(self, x, y):
        return any(z[0] <= x <= z[2] and z[1] <= y <= z[3] for z in self.zones)

    def _on_costmap(self, msg):
        info = msg.info
        data = np.asarray(msg.data, dtype=np.int16).reshape(info.height, info.width)
        self.costmap = (data, info.origin.position.x, info.origin.position.y, info.resolution)

    def _on_map(self, msg):
        if self.centers is not None:
            return
        info = msg.info
        res, ox, oy = info.resolution, info.origin.position.x, info.origin.position.y
        free = np.asarray(msg.data, dtype=np.int16).reshape(info.height, info.width) == 0
        n = max(1, int(round(self.cell_size / res)))

        centers, points = [], []
        for j0 in range(0, info.height, n):
            for i0 in range(0, info.width, n):
                blk = free[j0:j0 + n, i0:i0 + n]
                if blk.mean() < self.min_free_ratio:
                    continue
                cx = ox + (i0 + blk.shape[1] / 2.0) * res
                cy = oy + (j0 + blk.shape[0] / 2.0) * res
                if self._excluded(cx, cy):
                    continue
                js, iis = np.nonzero(blk)
                pts = np.stack([ox + (i0 + iis + 0.5) * res, oy + (j0 + js + 0.5) * res], axis=1)
                pts = pts[[not self._excluded(px, py) for px, py in pts]]
                if len(pts) == 0:
                    continue
                pts = pts[np.argsort(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy))]
                points.append(pts[::max(1, len(pts) // 150)])
                centers.append((cx, cy))

        self.centers = np.array(centers)
        self.points = points
        self.visited = np.zeros(len(centers), dtype=bool)
        self.fails = np.zeros(len(centers), dtype=int)
        self.get_logger().info(f'Mapa recibido: {len(centers)} zonas a recorrer')

    def _robot_xy(self):
        try:
            t = self.tf_buffer.lookup_transform(self.global_frame, self.robot_frame, Time())
            return t.transform.translation.x, t.transform.translation.y
        except Exception:
            return None

    def _cost(self, x, y):
        if self.costmap is None:
            return 0
        data, ox, oy, res = self.costmap
        i, j = int((x - ox) / res), int((y - oy) / res)
        if 0 <= j < data.shape[0] and 0 <= i < data.shape[1]:
            return int(data[j, i])
        return -1

    def _pick_point(self, cell):
        """Punto libre de la celda más cercano a su centro y lejos de paredes."""
        for x, y in self.points[cell]:
            c = self._cost(x, y)
            if 0 <= c <= self.max_goal_cost:
                return float(x), float(y)
        return None

    def _update_visited(self):
        if self.centers is None:
            return
        xy = self._robot_xy()
        if xy is None:
            return
        d = np.hypot(self.centers[:, 0] - xy[0], self.centers[:, 1] - xy[1])
        self.visited |= d <= self.visit_radius

    def _now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _tick(self):
        if self.state == 'WAIT':
            if self.centers is None or self._robot_xy() is None:
                return
            if not (self.nav_client.server_is_ready() and self.plan_client.server_is_ready()):
                return
            self.get_logger().info('Nav2 listo → empezando patrulla')
            self.state = 'SELECT'

        elif self.state == 'SELECT':
            self._select_candidates()

        elif self.state == 'NAVIGATING':
            if self.goal_handle is not None and self._now() - self.nav_start > self.goal_timeout:
                self.get_logger().warn(f'Goal excedió {self.goal_timeout:.0f} s → cancelando')
                self.goal_handle.cancel_goal_async()
                self.nav_start = float('inf')
            elif (why := self._near_goal_unreachable()):
                self._skip_near_goal(why)
            elif self._is_stuck():
                self._start_escape()

        elif self.state in ('ESCAPE_BACKUP', 'ESCAPE_NAV'):
            if self._now() > self.escape_deadline:
                self.get_logger().warn('Escape tardó demasiado → retomando goal')
                self._resume_goal()

        elif self.state == 'DWELL':
            if self._now() >= self.dwell_until:
                self.state = 'SELECT'

    def _select_candidates(self):
        xy = self._robot_xy()
        if xy is None:
            return
        pending = np.nonzero(~self.visited & (self.fails < self.max_failures))[0]
        if len(pending) == 0:
            pct = 100.0 * self.visited.mean() if len(self.visited) else 0.0
            self.get_logger().info(
                f'Ronda {self.round} terminada ({pct:.0f}% de zonas visitadas) → nueva ronda')
            self.round += 1
            self.visited[:] = False
            self.fails[:] = 0
            return

        d = np.hypot(self.centers[pending, 0] - xy[0], self.centers[pending, 1] - xy[1])
        self.plan_queue = []
        for cell in pending[np.argsort(d)]:
            p = self._pick_point(int(cell))
            if p is None:
                self.fails[cell] = self.max_failures
                continue
            self.plan_queue.append((int(cell), p))
            if len(self.plan_queue) >= self.candidates_per_try:
                break
        if not self.plan_queue:
            return
        self.plan_results = []
        self.state = 'PLANNING'
        self._plan_next()

    def _make_pose(self, x, y, yaw):
        ps = PoseStamped()
        ps.header.frame_id = self.global_frame
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x, ps.pose.position.y = x, y
        q = yaw_to_quat(yaw)
        (ps.pose.orientation.x, ps.pose.orientation.y,
         ps.pose.orientation.z, ps.pose.orientation.w) = q
        return ps

    def _plan_next(self):
        if not self.plan_queue:
            self._finish_planning()
            return
        cell, (x, y) = self.plan_queue.pop(0)
        goal = ComputePathToPose.Goal()
        goal.goal = self._make_pose(x, y, 0.0)
        goal.use_start = False
        fut = self.plan_client.send_goal_async(goal)
        fut.add_done_callback(lambda f: self._on_plan_accepted(f, cell, x, y))

    def _on_plan_accepted(self, fut, cell, x, y):
        gh = fut.result()
        if not gh.accepted:
            self.fails[cell] += 1
            self._plan_next()
            return
        gh.get_result_async().add_done_callback(lambda f: self._on_plan_result(f, cell, x, y))

    def _on_plan_result(self, fut, cell, x, y):
        res = fut.result()
        poses = res.result.path.poses if res.status == GoalStatus.STATUS_SUCCEEDED else []
        if len(poses) >= 2:
            pts = np.array([[p.pose.position.x, p.pose.position.y] for p in poses])
            length = float(np.sum(np.hypot(*np.diff(pts, axis=0).T)))
            a, b = pts[max(0, len(pts) - 6)], pts[-1]
            yaw = math.atan2(b[1] - a[1], b[0] - a[0])
            self.plan_results.append((length, cell, x, y, yaw))
        else:
            self.fails[cell] += 1
        self._plan_next()

    def _finish_planning(self):
        if not self.plan_results:
            self.state = 'SELECT'
            return
        length, cell, x, y, yaw = min(self.plan_results)
        self._send_goal(cell, x, y, yaw, length)

    def _send_goal(self, cell, x, y, yaw, length, resume=False):
        self.goal_seq += 1
        seq = self.goal_seq
        self.goal_cell, self.goal_xy = cell, (x, y)
        if resume:
            self.get_logger().info(f'Retomando goal → ({x:.2f}, {y:.2f})')
        else:
            self.goal = (cell, x, y, yaw, length)
            self.escapes = 0
            self.escape_history = []
            self.near_since = None
            self.nav_start = self._now()
            left = int(np.sum(~self.visited & (self.fails < self.max_failures)))
            self.get_logger().info(
                f'[ronda {self.round}] Goal → ({x:.2f}, {y:.2f})  ruta {length:.1f} m  '
                f'(quedan {left} zonas)')
        goal = NavigateToPose.Goal()
        goal.pose = self._make_pose(x, y, yaw)
        self.state = 'NAVIGATING'
        self._reset_anchor()
        self.nav_fb = None
        self.near_recoveries = 0
        self.detour_ticks = 0
        fut = self.nav_client.send_goal_async(
            goal, feedback_callback=lambda m: self._on_nav_fb(m, seq))
        fut.add_done_callback(lambda f: self._on_nav_accepted(f, seq))

    def _on_nav_fb(self, msg, seq):
        if seq == self.goal_seq:
            self.nav_fb = msg.feedback

    def _on_nav_accepted(self, fut, seq):
        gh = fut.result()
        if seq != self.goal_seq:
            return
        if not gh.accepted:
            self.get_logger().warn('Nav2 rechazó el goal')
            self.fails[self.goal_cell] += 1
            self._start_dwell(1.0)
            return
        self.goal_handle = gh
        gh.get_result_async().add_done_callback(lambda f: self._on_nav_result(f, seq))

    def _on_nav_result(self, fut, seq):
        if seq != self.goal_seq:
            return
        status = fut.result().status
        self.goal_handle = None
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.visited[self.goal_cell] = True
            self.get_logger().info(f'Llegó. Esperando {self.dwell_time:.0f} s...')
            self._start_dwell(self.dwell_time)
        elif status == GoalStatus.STATUS_ABORTED and self._goal_dist() < self.near_goal_dist:
            self._skip_near_goal('Nav2 abortó estando cerca')
        elif (status == GoalStatus.STATUS_ABORTED and self.escapes < self.max_escapes
              and self._now() - self.nav_start < self.goal_timeout):
            self.get_logger().warn('Goal abortado por Nav2 → intentando escape')
            self._start_escape()
        else:
            self.fails[self.goal_cell] += 1
            name = {GoalStatus.STATUS_CANCELED: 'cancelado',
                    GoalStatus.STATUS_ABORTED: 'abortado'}.get(status, str(status))
            self.get_logger().warn(f'Goal {name} → buscando otra zona')
            self._start_dwell(1.0)

    def _start_dwell(self, seconds):
        self.dwell_until = self._now() + seconds
        self.state = 'DWELL'

    def _goal_dist(self):
        xy = self._robot_xy()
        if xy is None or self.goal_xy is None:
            return float('inf')
        return math.hypot(xy[0] - self.goal_xy[0], xy[1] - self.goal_xy[1])

    def _near_goal_unreachable(self):
        """Motivo (str) para omitir el goal si está cerca pero no se logra llegar, si no ''."""
        if self.goal_handle is None:
            return ''
        d = self._goal_dist()
        if d > self.near_goal_dist + 0.5:
            self.near_since = None
            return ''
        if d > self.near_goal_dist:
            return ''
        fb = self.nav_fb
        if self.near_since is None:
            self.near_since = self._now()
            self.near_recoveries = fb.number_of_recoveries if fb else self.near_recoveries
            self.get_logger().info(f'Cerca del goal ({d:.1f} m)')

        if self._cost(*self.goal_xy) > self.max_goal_cost:
            return 'el punto quedó bloqueado por un obstáculo'
        if fb is not None:
            if fb.number_of_recoveries > self.near_recoveries:
                return 'Nav2 entró en recuperación'
            if fb.distance_remaining > self.near_detour_ratio * d + 0.5:
                self.detour_ticks += 1
                if self.detour_ticks >= 3:
                    return f'Nav2 propone un rodeo de {fb.distance_remaining:.1f} m'
            else:
                self.detour_ticks = 0
        if self._now() - self.near_since > self.near_goal_timeout:
            return f'{self.near_goal_timeout:.0f} s cerca sin llegar'
        return ''

    def _skip_near_goal(self, why):
        self.get_logger().warn(f'Omitiendo goal a {self._goal_dist():.1f} m: {why} → siguiente')
        self._abort_current()
        self.visited[self.goal_cell] = True
        self._start_dwell(0.5)

    def _reset_anchor(self):
        xy = self._robot_xy()
        self.anchor = (xy[0], xy[1], self._now()) if xy else None

    def _is_stuck(self):
        """True si lleva stuck_time s sin alejarse stuck_radius del último punto de avance."""
        xy = self._robot_xy()
        if xy is None or self.goal_handle is None:
            return False
        if self.anchor is None or math.hypot(xy[0] - self.anchor[0],
                                             xy[1] - self.anchor[1]) > self.stuck_radius:
            self.anchor = (xy[0], xy[1], self._now())
            return False
        if math.hypot(xy[0] - self.goal_xy[0], xy[1] - self.goal_xy[1]) < 0.5:
            return False
        return self._now() - self.anchor[2] > self.stuck_time

    def _start_escape(self):
        self.escapes += 1
        if self.escapes > self.max_escapes:
            self.get_logger().warn(f'{self.max_escapes} escapes sin éxito → saltando zona')
            self._abort_current()
            self.fails[self.goal_cell] += 1
            self._start_dwell(1.0)
            return
        self.get_logger().warn(
            f'Robot atascado (escape {self.escapes}/{self.max_escapes}) → retrocediendo')
        self._abort_current()
        self.escape_deadline = self._now() + self.escape_timeout
        if self.backup_dist <= 0.0 or not self.backup_client.server_is_ready():
            self._escape_nav()
            return
        self.goal_seq += 1
        seq = self.goal_seq
        self.state = 'ESCAPE_BACKUP'
        goal = BackUp.Goal()
        goal.target.x = self.backup_dist
        goal.speed = self.backup_speed
        t = self.backup_dist / max(self.backup_speed, 0.01) + 5.0
        goal.time_allowance = Duration(sec=int(t), nanosec=int((t % 1) * 1e9))
        fut = self.backup_client.send_goal_async(goal)
        fut.add_done_callback(lambda f: self._on_escape_accepted(f, seq, self._escape_nav))

    def _abort_current(self):
        """Invalida callbacks pendientes y cancela la acción en curso."""
        self.goal_seq += 1
        if self.goal_handle is not None:
            self.goal_handle.cancel_goal_async()
            self.goal_handle = None

    def _find_escape_point(self):
        """Punto libre de bajo costo en un anillo alrededor del robot, hacia el goal."""
        xy = self._robot_xy()
        if xy is None or self.costmap is None:
            return None
        data, ox, oy, res = self.costmap
        r = int(self.escape_max_dist / res) + 1
        ci, cj = int((xy[0] - ox) / res), int((xy[1] - oy) / res)
        i0, i1 = max(0, ci - r), min(data.shape[1], ci + r + 1)
        j0, j1 = max(0, cj - r), min(data.shape[0], cj + r + 1)
        if i0 >= i1 or j0 >= j1:
            return None
        sub = data[j0:j1, i0:i1]
        jj, ii = np.mgrid[j0:j1, i0:i1]
        px, py = ox + (ii + 0.5) * res, oy + (jj + 0.5) * res
        d = np.hypot(px - xy[0], py - xy[1])
        ok = ((sub >= 0) & (sub <= self.escape_max_cost)
              & (d >= self.escape_min_dist) & (d <= self.escape_max_dist))
        px, py, cost = px[ok], py[ok], sub[ok].astype(float)
        if len(px) == 0:
            return None
        score = cost + 10.0 * np.hypot(px - self.goal_xy[0], py - self.goal_xy[1])
        for hx, hy in self.escape_history:
            score += 200.0 * (np.hypot(px - hx, py - hy) < 0.7)
        keep = [k for k in np.argsort(score)[:50] if not self._excluded(px[k], py[k])]
        if not keep:
            return None
        return float(px[keep[0]]), float(py[keep[0]])

    def _escape_nav(self):
        p = self._find_escape_point()
        if p is None:
            self.get_logger().warn('Sin punto de escape libre cerca → retomando goal')
            self._resume_goal()
            return
        self.escape_xy = p
        self.escape_history.append(p)
        xy = self._robot_xy() or p
        yaw = math.atan2(p[1] - xy[1], p[0] - xy[0])
        self.get_logger().info(f'Escape → punto libre ({p[0]:.2f}, {p[1]:.2f})')
        self.goal_seq += 1
        seq = self.goal_seq
        self.state = 'ESCAPE_NAV'
        goal = NavigateToPose.Goal()
        goal.pose = self._make_pose(p[0], p[1], yaw)
        fut = self.nav_client.send_goal_async(goal)
        fut.add_done_callback(lambda f: self._on_escape_accepted(f, seq, self._resume_goal))

    def _on_escape_accepted(self, fut, seq, next_step):
        gh = fut.result()
        if seq != self.goal_seq:
            return
        if not gh.accepted:
            next_step()
            return
        self.goal_handle = gh
        gh.get_result_async().add_done_callback(
            lambda f: self._on_escape_result(f, seq, next_step))

    def _on_escape_result(self, fut, seq, next_step):
        if seq != self.goal_seq:
            return
        self.goal_handle = None
        ok = fut.result().status == GoalStatus.STATUS_SUCCEEDED
        self.get_logger().info(
            f'{"Retroceso" if self.state == "ESCAPE_BACKUP" else "Escape"} '
            f'{"completado" if ok else "falló"}')
        next_step()

    def _resume_goal(self):
        self._abort_current()
        self.escape_xy = None
        cell, x, y, yaw, length = self.goal
        self._send_goal(cell, x, y, yaw, length, resume=True)

    def cancel_active_goal(self):
        """Cancela el goal en curso (al apagar el nodo) y espera la confirmación."""
        if self.goal_handle is None:
            return
        self.get_logger().info('Cancelando goal activo...')
        fut = self.goal_handle.cancel_goal_async()
        rclpy.spin_until_future_complete(self, fut, timeout_sec=3.0)

    def _publish_markers(self):
        if self.centers is None:
            return
        stamp = self.get_clock().now().to_msg()
        arr = MarkerArray()

        def base(mid, ns, mtype):
            m = Marker()
            m.header.frame_id, m.header.stamp = self.global_frame, stamp
            m.ns, m.id, m.type, m.action = ns, mid, mtype, Marker.ADD
            m.pose.orientation.w = 1.0
            return m

        skipped = self.fails >= self.max_failures
        groups = [('visitadas', self.visited, (0.1, 0.8, 0.1, 0.35)),
                  ('pendientes', ~self.visited & ~skipped, (1.0, 0.6, 0.0, 0.35)),
                  ('saltadas', ~self.visited & skipped, (0.5, 0.5, 0.5, 0.35))]
        for k, (ns, mask, rgba) in enumerate(groups):
            m = base(k, ns, Marker.CUBE_LIST)
            m.scale.x = m.scale.y = self.cell_size * 0.8
            m.scale.z = 0.02
            m.color.r, m.color.g, m.color.b, m.color.a = rgba
            m.points = [Point(x=float(x), y=float(y), z=0.01) for x, y in self.centers[mask]]
            if not m.points:
                m.action = Marker.DELETE
            arr.markers.append(m)

        for k, (x0, y0, x1, y1, name) in enumerate(self.zones):
            m = base(10 + k, 'zonas_excluidas', Marker.LINE_STRIP)
            m.scale.x = 0.08
            m.color.r, m.color.a = 1.0, 1.0
            m.points = [Point(x=x, y=y, z=0.05) for x, y in
                        [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]]
            arr.markers.append(m)
            t = base(30 + k, 'zonas_excluidas_nombre', Marker.TEXT_VIEW_FACING)
            t.pose.position.x, t.pose.position.y, t.pose.position.z = (x0 + x1) / 2, (y0 + y1) / 2, 0.5
            t.scale.z = 0.4
            t.color.r = t.color.g = t.color.b = t.color.a = 1.0
            t.text = name
            arr.markers.append(t)

        e = base(101, 'escape', Marker.SPHERE)
        if self.escape_xy and self.state == 'ESCAPE_NAV':
            e.pose.position.x, e.pose.position.y, e.pose.position.z = *self.escape_xy, 0.2
            e.scale.x = e.scale.y = e.scale.z = 0.35
            e.color.r, e.color.g, e.color.a = 1.0, 0.2, 0.9
        else:
            e.action = Marker.DELETE
        arr.markers.append(e)

        g = base(100, 'goal', Marker.CYLINDER)
        if self.goal_xy and self.state in ('NAVIGATING', 'DWELL', 'ESCAPE_BACKUP', 'ESCAPE_NAV'):
            g.pose.position.x, g.pose.position.y, g.pose.position.z = *self.goal_xy, 0.25
            g.scale.x = g.scale.y = 0.4
            g.scale.z = 0.5
            g.color.b, g.color.g, g.color.a = 1.0, 0.4, 0.8
        else:
            g.action = Marker.DELETE
        arr.markers.append(g)
        self.marker_pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = PatrolNode()

    stop = {'flag': False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__('flag', True))
    try:
        while rclpy.ok() and not stop['flag']:
            rclpy.spin_once(node, timeout_sec=0.1)
        if rclpy.ok():
            node.cancel_active_goal()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

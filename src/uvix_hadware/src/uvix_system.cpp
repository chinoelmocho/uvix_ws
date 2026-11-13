#include "hardware_interface/system_interface.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_lifecycle/state.hpp"
#include "pluginlib/class_list_macros.hpp"
#include <vector>
#include <cmath>

namespace uvix_hardware
{

using CallbackReturn = hardware_interface::CallbackReturn;
using ReturnType = hardware_interface::return_type;


class UvixSystem : public hardware_interface::SystemInterface{
public:

    std::vector<hardware_interface::StateInterface>
    export_state_interfaces() override
    {
        std::vector<hardware_interface::StateInterface> interfaces;

        interfaces.emplace_back(
            "base_link_wheel_left_joint", "position", &posicion_izq_);

        interfaces.emplace_back(
            "base_link_wheel_left_joint", "velocity", &velocidad_izq_);

        interfaces.emplace_back(
            "base_link_wheel_right_joint", "position", &posicion_der_);

        interfaces.emplace_back(
            "base_link_wheel_right_joint", "velocity", &velocidad_der_);

        return interfaces;
    }


    std::vector<hardware_interface::CommandInterface>
    export_command_interfaces() override
    {
        std::vector<hardware_interface::CommandInterface> interfaces;

        interfaces.emplace_back(
            "base_link_wheel_left_joint", "velocity", &comando_izq_);

        interfaces.emplace_back(
            "base_link_wheel_right_joint", "velocity", &comando_der_);

        return interfaces;
    }







    hardware_interface::CallbackReturn on_init(
        const hardware_interface::HardwareInfo & info) override
    {
        return hardware_interface::SystemInterface::on_init(info);
    }



    hardware_interface::CallbackReturn on_configure(
        const rclcpp_lifecycle::State &) override
    {
        detener_simulacion();


        posicion_izq_ = 0.0;
        posicion_der_ = 0.0;

        RCLCPP_INFO(
            rclcpp::get_logger("UvixSystem"),
            "Preparando el sistema simulado"
        );

        return hardware_interface::CallbackReturn::SUCCESS;
    }

    hardware_interface::CallbackReturn on_activate(
        const rclcpp_lifecycle::State &) override
    {
        detener_simulacion();
        activo_ = true;

        RCLCPP_INFO(
            rclcpp::get_logger("UvixSystem"),
            "Sistema simulado activado"
        );

        return hardware_interface::CallbackReturn::SUCCESS;
    }
    hardware_interface::CallbackReturn on_deactivate(
        const rclcpp_lifecycle::State &) override
    {
        detener_simulacion();

        RCLCPP_INFO(
            rclcpp::get_logger("UvixSystem"),
            "Sistema simulado desactivado"
        );

        return hardware_interface::CallbackReturn::SUCCESS;
    }

    hardware_interface::return_type read(
        const rclcpp::Time &,
        const rclcpp::Duration & period) override
    {

        const double dt = period.seconds();

        if (!std::isfinite(dt) || dt < 0.0)
        {
            detener_simulacion();

            return ReturnType::ERROR;
        }

        if (activo_)
        {
            // Modelo ideal: velocidad alcanzada = velocidad aplicada.
            velocidad_izq_ = velocidad_aplicada_izq_;
            velocidad_der_ = velocidad_aplicada_der_;
        }
        else
        {
            velocidad_izq_ = 0.0;
            velocidad_der_ = 0.0;
        }


        posicion_izq_ += velocidad_izq_ * dt;
        posicion_der_ += velocidad_der_ * dt;

        return ReturnType::OK;
    }

    hardware_interface::return_type write(
        const rclcpp::Time &,
        const rclcpp::Duration &) override
    {

        if (!activo_)
        {
            velocidad_aplicada_izq_ = 0.0;
            velocidad_aplicada_der_ = 0.0;

            return ReturnType::OK;
        }

        // Comprobar que las órdenes no sean NaN o infinito.
        if (
            !std::isfinite(comando_izq_) ||
            !std::isfinite(comando_der_))
        {
            detener_simulacion();

            return ReturnType::ERROR;
        }


        velocidad_aplicada_izq_ = comando_izq_;
        velocidad_aplicada_der_ = comando_der_;

        return ReturnType::OK;
    }
private:

    double posicion_izq_ = 0.0;
    double velocidad_izq_ = 0.0;


    double posicion_der_ = 0.0;
    double velocidad_der_ = 0.0;


    double comando_izq_ = 0.0;
    double comando_der_ = 0.0;


    double velocidad_aplicada_izq_ = 0.0;
    double velocidad_aplicada_der_ = 0.0;

    bool activo_ = false;


    void detener_simulacion()
    {
        activo_ = false;

        comando_izq_ = 0.0;
        comando_der_ = 0.0;

        velocidad_aplicada_izq_ = 0.0;
        velocidad_aplicada_der_ = 0.0;

        velocidad_izq_ = 0.0;
        velocidad_der_ = 0.0;
    }
};
}



PLUGINLIB_EXPORT_CLASS(
    uvix_hardware::UvixSystem,
    hardware_interface::SystemInterface
)

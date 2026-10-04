import {
    FaCheckCircle,
    FaTimesCircle,
    FaInfoCircle,
    FaExclamationTriangle,
    FaTimes
} from "react-icons/fa";

const styles = {
    success: {
        icon: <FaCheckCircle size={22} />,
        border: "border-green-500",
        bg: "bg-[#1A2E20]",
        text: "text-green-400",
    },

    error: {
        icon: <FaTimesCircle size={22} />,
        border: "border-red-500",
        bg: "bg-[#2B1C1C]",
        text: "text-red-400",
    },

    warning: {
        icon: <FaExclamationTriangle size={22} />,
        border: "border-yellow-500",
        bg: "bg-[#2E2817]",
        text: "text-yellow-400",
    },

    info: {
        icon: <FaInfoCircle size={22} />,
        border: "border-[#FFB703]",
        bg: "bg-[#232F3E]",
        text: "text-[#FFB703]",
    },
};

export default function Toast({

    type = "success",
    title,
    message,
    onClose

}) {

    const style = styles[type];

    return (

        <div
            className={`
            flex
            items-start
            gap-4
            rounded-xl
            border
            ${style.border}
            ${style.bg}
            p-4
            shadow-2xl
            backdrop-blur
            animate-slide-in
            `}
        >

            <div className={style.text}>

                {style.icon}

            </div>

            <div className="flex-1">

                <h3 className="font-bold">

                    {title}

                </h3>

                <p className="mt-1 text-sm text-gray-300">

                    {message}

                </p>

            </div>

            <button
                onClick={onClose}
                className="text-gray-400 hover:text-white"
            >

                <FaTimes size={18} />

            </button>

        </div>

    );

}
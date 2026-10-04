import { useState } from "react";

export default function useToast() {

    const [toast, setToast] = useState(null);

    function showToast(component) {

        setToast(component);

    }

    function clearToast() {

        setToast(null);

    }

    return {

        toast,
        showToast,
        clearToast

    };

}
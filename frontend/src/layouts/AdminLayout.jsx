import { Outlet } from "react-router-dom";

export default function AdminLayout() {
    return (
        <div className="min-h-screen bg-[#131921] text-white">
            <Outlet />
        </div>
    );
}
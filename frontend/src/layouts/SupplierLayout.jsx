import { Suspense } from "react";
import { Outlet } from "react-router-dom";

export default function SupplierLayout() {
  return (
    <div className="min-h-screen bg-[#131921] text-white">
      <Suspense
        fallback={
          <div className="min-h-screen bg-[#131921] text-white flex items-center justify-center">
            Loading supplier workspace…
          </div>
        }
      >
        <Outlet />
      </Suspense>
    </div>
  );
}

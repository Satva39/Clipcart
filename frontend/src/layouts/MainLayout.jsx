import { Suspense } from "react";
import { Outlet } from "react-router-dom";
import Navbar from "../components/layout/Navbar";
import MenuBar from "../components/layout/MenuBar";
import Footer from "../components/layout/Footer";
import ScrollToTop from "../components/common/ScrollToTop";

export default function MainLayout() {
  return (
    <div className="cc-app">
      <ScrollToTop />
      <Navbar />
      <MenuBar />
      <main className="cc-main">
        <Suspense
          fallback={
            <div className="cc-page-shell">
              <div className="cc-container" aria-busy="true">
                Loading…
              </div>
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}

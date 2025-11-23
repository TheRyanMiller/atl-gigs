import { Link, useLocation } from "react-router-dom";

export default function Navigation() {
  const location = useLocation();

  return (
    <nav className="bg-white shadow-sm">
      <div className="container mx-auto px-4">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link
              to="/"
              className={`inline-flex items-center px-4 pt-1 text-sm font-medium ${
                location.pathname === "/"
                  ? "border-b-2 border-blue-500 text-gray-900"
                  : "text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              Events
            </Link>
            <Link
              to="/status"
              className={`inline-flex items-center px-4 pt-1 text-sm font-medium ${
                location.pathname === "/status"
                  ? "border-b-2 border-blue-500 text-gray-900"
                  : "text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              Status
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

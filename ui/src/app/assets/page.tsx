"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function AssetsPage() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [user, setUser] = useState<any>(null);

  // Check authentication on component mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch("http://localhost:8000/auth/me", {
          credentials: "include",
        });
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
          router.push("/login");
        }
      } catch (error) {
        setIsAuthenticated(false);
        router.push("/login");
      }
    };

    checkAuth();
  }, [router]);

  // Redirect non-admin users
  useEffect(() => {
    if (isAuthenticated === false) {
      router.push("/login");
    } else if (user && user.role !== "admin") {
      router.push("/");
    }
  }, [isAuthenticated, user, router]);

  if (isAuthenticated === null || !user || user.role !== "admin") {
    return (
      <div className="flex items-center justify-center min-h-screen">
        Loading...
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 text-white p-4">
        <h2 className="text-xl font-bold mb-4">Navigation</h2>
        <ul>
          <li className="mb-2">
            <a href="/" className="hover:text-gray-300">
              Dashboard
            </a>
          </li>
          {user && user.role === "admin" && (
            <>
              <li className="mb-2">
                <a href="/approvers" className="hover:text-gray-300">
                  Approvers
                </a>
              </li>
              <li className="mb-2">
                <a href="/engineers" className="hover:text-gray-300">
                  Engineers
                </a>
              </li>
              <li className="mb-2">
                <a href="/users" className="hover:text-gray-300">
                  Users
                </a>
              </li>
              <li className="mb-2">
                <a href="/assets" className="text-blue-300 font-semibold">
                  Asset Management
                </a>
              </li>
              <li className="mb-2">
                <a href="/settings" className="hover:text-gray-300">
                  Settings
                </a>
              </li>
            </>
          )}
          <li className="mt-8 pt-4 border-t border-gray-600">
            <button
              onClick={async () => {
                try {
                  await fetch("http://localhost:8000/auth/logout", {
                    method: "POST",
                    credentials: "include",
                  });
                  window.location.href = "/login";
                } catch (error) {
                  console.error("Logout error:", error);
                  window.location.href = "/login";
                }
              }}
              className="w-full text-left hover:text-gray-300 text-red-300"
            >
              Logout
            </button>
          </li>
        </ul>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <h1 className="text-3xl font-bold mb-6">Asset Management</h1>
        <div className="bg-white p-6 rounded-lg shadow-md">
          <p className="text-gray-600 text-center">Coming Soon...</p>
          <p className="text-sm text-gray-500 text-center mt-2">
            Asset management functionality will be available here once the
            backend API is implemented.
          </p>
        </div>
      </div>
    </div>
  );
}

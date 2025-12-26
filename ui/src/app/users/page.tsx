"use client";

import { useEffect, useState, useMemo } from "react";
import { LoginUser } from "../types";

export default function Users() {
  const [users, setUsers] = useState<LoginUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<LoginUser | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    department: "",
    password: "",
  });
  const [editFormData, setEditFormData] = useState({
    name: "",
    email: "",
    department: "",
    password: "",
  });

  const [user, setUser] = useState<any>(null);

  // Check if create form is valid (all fields must be filled)
  const isCreateFormValid = useMemo(() => {
    return (
      formData.name.trim() !== "" &&
      formData.email.trim() !== "" &&
      formData.department !== "" &&
      formData.password.trim() !== ""
    );
  }, [formData]);

  // Check if edit form is valid (name, email, department must be filled, password optional)
  const isEditFormValid = useMemo(() => {
    return (
      editFormData.name.trim() !== "" &&
      editFormData.email.trim() !== "" &&
      editFormData.department !== ""
    );
  }, [editFormData]);

  // Fetch users on component mount
  useEffect(() => {
    fetchUsers();
  }, []);

  // Fetch current user
  useEffect(() => {
    fetch("http://localhost:8000/auth/me", { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setUser(data))
      .catch(() => setUser(null));
  }, []);

  // Function to fetch users from backend
  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/login");
      const data = await response.json();
      if (response.ok) {
        setUsers(data.login || []);
      } else {
        setError(data.error || "Failed to fetch users");
      }
    } catch (err) {
      setError("Failed to fetch users");
    } finally {
      setLoading(false);
    }
  };

  // Handle form input changes
  const handleFormChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  // Handle form submission for creating a new user
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check for duplicate name
    const existingUserByName = users.find(
      (u) => u.name.toLowerCase() === formData.name.toLowerCase()
    );
    if (existingUserByName) {
      alert("A user with this username already exists.");
      return;
    }

    // Check for duplicate email
    const existingUser = users.find(
      (u) => u.email.toLowerCase() === formData.email.toLowerCase()
    );
    if (existingUser) {
      alert("A user with this email already exists.");
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          department: formData.department,
          password: formData.password,
        }),
      });
      const data = await response.json();
      if (response.ok) {
        setFormData({
          name: "",
          email: "",
          department: "",
          password: "",
        });
        // Refresh users list
        fetchUsers();
        setShowCreateModal(false);
      } else {
        alert(data.error || "Failed to create user");
      }
    } catch (error) {
      alert("Failed to create user");
    }
  };

  // Handle row click to open edit modal
  const handleRowClick = (user: LoginUser) => {
    setSelectedUser(user);
    setEditFormData({
      name: user.name,
      email: user.email,
      department: user.department,
      password: "",
    });
    setShowEditModal(true);
  };

  // Handle edit form input changes
  const handleEditFormChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    setEditFormData({
      ...editFormData,
      [e.target.name]: e.target.value,
    });
  };

  // Handle edit form submission
  const handleEditFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    // Check for duplicate name (excluding current user)
    const existingUserByName = users.find(
      (u) =>
        u.name.toLowerCase() === editFormData.name.toLowerCase() &&
        u.id !== selectedUser.id
    );
    if (existingUserByName) {
      alert("A user with this username already exists.");
      return;
    }

    // Check for duplicate email (excluding current user)
    const existingUser = users.find(
      (u) =>
        u.email.toLowerCase() === editFormData.email.toLowerCase() &&
        u.id !== selectedUser.id
    );
    if (existingUser) {
      alert("A user with this email already exists.");
      return;
    }

    try {
      const updateData: any = {
        name: editFormData.name,
        email: editFormData.email,
        department: editFormData.department,
      };
      if (editFormData.password.trim() !== "") {
        updateData.password = editFormData.password;
      }

      const response = await fetch(
        `http://localhost:8000/login/${selectedUser.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(updateData),
        }
      );
      const data = await response.json();
      if (response.ok) {
        fetchUsers();
        setShowEditModal(false);
      } else {
        alert(data.error || "Failed to update user");
      }
    } catch (error) {
      alert("Failed to update user");
    }
  };

  // Handle user deletion
  const handleDeleteUser = async () => {
    if (!selectedUser) return;

    if (!confirm(`Are you sure you want to delete ${selectedUser.name}?`)) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/login/${selectedUser.id}`,
        {
          method: "DELETE",
        }
      );
      const data = await response.json();
      if (response.ok && !data.error) {
        fetchUsers();
        setShowEditModal(false);
      } else {
        alert(data.error || "Failed to delete user");
      }
    } catch (error) {
      alert("Failed to delete user");
    }
  };

  // Close edit modal
  const closeEditModal = () => {
    setShowEditModal(false);
    setSelectedUser(null);
    setEditFormData({
      name: "",
      email: "",
      department: "",
      password: "",
    });
  };

  // Close create modal
  const closeCreateModal = () => {
    setShowCreateModal(false);
    setFormData({
      name: "",
      email: "",
      department: "",
      password: "",
    });
  };

  // Handle logout
  const handleLogout = async () => {
    try {
      await fetch("http://localhost:8000/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      // Redirect to login
      window.location.href = "/login";
    } catch (error) {
      console.error("Logout error:", error);
      // Still redirect even if logout fails
      window.location.href = "/login";
    }
  };

  // Render loading, error, and main content
  if (loading)
    return (
      <div className="flex items-center justify-center min-h-screen">
        Loading users...
      </div>
    );
  if (error)
    return (
      <div className="flex items-center justify-center min-h-screen text-red-600">
        Error: {error}
      </div>
    );

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
                <a href="/users" className="text-blue-300 font-semibold">
                  Users
                </a>
              </li>
              <li className="mb-2">
                <a href="/assets" className="hover:text-gray-300">
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
              onClick={handleLogout}
              className="w-full text-left hover:text-gray-300 text-red-300"
            >
              Logout
            </button>
          </li>
        </ul>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Users</h1>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Create User
          </button>
        </div>

        {/* Users Table */}
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="p-3 bg-gray-100">
            <h2 className="text-xl font-semibold">All Users</h2>
          </div>
          <div className="overflow-x-auto max-h-[calc(100vh-180px)] overflow-y-auto">
            <table className="w-full table-fixed">
              <thead className="bg-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left w-1/6">ID</th>
                  <th className="px-4 py-2 text-left w-2/6">Name</th>
                  <th className="px-4 py-2 text-left w-2/6">Email</th>
                  <th className="px-4 py-2 text-left w-1/6">Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleRowClick(user)}
                  >
                    <td className="px-4 py-2 truncate">{user.id}</td>
                    <td className="px-4 py-2 truncate">{user.name}</td>
                    <td className="px-4 py-2 truncate">{user.email}</td>
                    <td className="px-4 py-2 truncate">{user.department}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create User Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-lg shadow-lg max-w-2xl w-full mx-4 max-h-[100vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Create New User</h2>
                <button
                  onClick={closeCreateModal}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>

              <form onSubmit={handleFormSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Role
                    </label>
                    <select
                      name="department"
                      value={formData.department}
                      onChange={handleFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select Role</option>
                      <option value="admin">Admin</option>
                      <option value="user">User</option>
                      <option value="auditor">Auditor</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="flex justify-end space-x-4 mt-6">
                  <button
                    type="button"
                    onClick={closeCreateModal}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!isCreateFormValid}
                    className={`px-4 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      isCreateFormValid
                        ? "bg-blue-600 text-white hover:bg-blue-700"
                        : "bg-gray-400 text-gray-200 cursor-not-allowed"
                    }`}
                  >
                    Create User
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit User Modal */}
        {showEditModal && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <h2 className="text-2xl font-bold mb-6">Edit User</h2>
              <form onSubmit={handleEditFormSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={editFormData.name}
                      onChange={handleEditFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      name="email"
                      value={editFormData.email}
                      onChange={handleEditFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Role
                    </label>
                    <select
                      name="department"
                      value={editFormData.department}
                      onChange={handleEditFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select Role</option>
                      <option value="admin">Admin</option>
                      <option value="user">User</option>
                      <option value="auditor">Auditor</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      New Password (leave blank to keep current)
                    </label>
                    <input
                      type="password"
                      name="password"
                      value={editFormData.password}
                      onChange={handleEditFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="flex justify-between space-x-4 mt-6">
                  <button
                    type="button"
                    onClick={handleDeleteUser}
                    className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    Delete User
                  </button>
                  <div className="flex space-x-4">
                    <button
                      type="button"
                      onClick={closeEditModal}
                      className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={!isEditFormValid}
                      className={`px-4 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                        isEditFormValid
                          ? "bg-blue-600 text-white hover:bg-blue-700"
                          : "bg-gray-400 text-gray-200 cursor-not-allowed"
                      }`}
                    >
                      Update User
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState, useMemo } from "react";
import { Fixer } from "../types";

export default function Fixers() {
  const [fixers, setFixers] = useState<Fixer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedFixer, setSelectedFixer] = useState<Fixer | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    email: "",
    department: "",
  });
  const [editFormData, setEditFormData] = useState({
    name: "",
    phone: "",
    email: "",
    department: "",
  });

  // Check if create form is valid (all fields must be filled)
  const isCreateFormValid = useMemo(() => {
    return (
      formData.name.trim() !== "" &&
      formData.phone.trim() !== "" &&
      formData.email.trim() !== "" &&
      formData.department !== ""
    );
  }, [formData]);

  // Check if edit form is valid (all fields must be filled)
  const isEditFormValid = useMemo(() => {
    return (
      editFormData.name.trim() !== "" &&
      editFormData.phone.trim() !== "" &&
      editFormData.email.trim() !== "" &&
      editFormData.department !== ""
    );
  }, [editFormData]);

  // Fetch fixers on component mount
  useEffect(() => {
    fetchFixers();
  }, []);

  // Function to fetch fixers from backend
  const fetchFixers = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/fixers");
      const data = await response.json();
      if (response.ok) {
        setFixers(data.fixers || []);
      } else {
        setError(data.error || "Failed to fetch fixers");
      }
    } catch (err) {
      setError("Failed to fetch fixers");
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

  //  Handle form submission for creating a new fixer
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check for duplicate name
    const existingFixerByName = fixers.find(
      (f) => f.name.toLowerCase() === formData.name.toLowerCase()
    );
    if (existingFixerByName) {
      alert("A fixer with this name already exists.");
      return;
    }

    // Check for duplicate email
    const existingFixer = fixers.find(
      (f) => f.email.toLowerCase() === formData.email.toLowerCase()
    );
    if (existingFixer) {
      alert("A fixer with this email already exists.");
      return;
    }

    // Check for duplicate phone
    const existingFixerByPhone = fixers.find((f) => f.phone === formData.phone);
    if (existingFixerByPhone) {
      alert("A fixer with this phone number already exists.");
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/fixers", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: formData.name,
          phone: formData.phone,
          email: formData.email,
          department: formData.department,
        }),
      });
      const data = await response.json();
      if (response.ok) {
        setFormData({
          name: "",
          phone: "",
          email: "",
          department: "",
        });
        // Refresh fixers list
        fetchFixers();
        setShowCreateModal(false);
      } else {
        // Error handled silently
      }
    } catch (error) {
      // Error handled silently
    }
  };

  // Handle row click to open edit modal
  const handleRowClick = (fixer: Fixer) => {
    setSelectedFixer(fixer);
    setEditFormData({
      name: fixer.name,
      phone: fixer.phone || "",
      email: fixer.email,
      department: fixer.department || "",
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
    if (!selectedFixer) return;

    // Check for duplicate name (excluding current fixer)
    const existingFixerByName = fixers.find(
      (f) =>
        f.name.toLowerCase() === editFormData.name.toLowerCase() &&
        f.id !== selectedFixer.id
    );
    if (existingFixerByName) {
      alert("A fixer with this name already exists.");
      return;
    }

    // Check for duplicate email (excluding current fixer)
    const existingFixer = fixers.find(
      (f) =>
        f.email.toLowerCase() === editFormData.email.toLowerCase() &&
        f.id !== selectedFixer.id
    );
    if (existingFixer) {
      alert("A fixer with this email already exists.");
      return;
    }

    // Check for duplicate phone (excluding current fixer)
    const existingFixerByPhone = fixers.find(
      (f) => f.phone === editFormData.phone && f.id !== selectedFixer.id
    );
    if (existingFixerByPhone) {
      alert("A fixer with this phone number already exists.");
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/fixers/${selectedFixer.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: editFormData.name,
            phone: editFormData.phone,
            email: editFormData.email,
            department: editFormData.department,
          }),
        }
      );
      const data = await response.json();
      if (response.ok) {
        fetchFixers();
        setShowEditModal(false);
      } else {
        // Error handled silently
      }
    } catch (error) {
      // Error handled silently
    }
  };

  //  Handle fixer deletion
  const handleDeleteFixer = async () => {
    if (!selectedFixer) return;

    if (!confirm(`Are you sure you want to delete ${selectedFixer.name}?`)) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/fixers/${selectedFixer.id}`,
        {
          method: "DELETE",
        }
      );
      const data = await response.json();
      if (response.ok) {
        fetchFixers();
        setShowEditModal(false);
      } else {
        // Error handled silently
      }
    } catch (error) {
      // Error handled silently
    }
  };

  // Close edit model
  const closeEditModal = () => {
    setShowEditModal(false);
    setSelectedFixer(null);
    setEditFormData({
      name: "",
      phone: "",
      email: "",
      department: "",
    });
  };

  // Close create modal
  const closeCreateModal = () => {
    setShowCreateModal(false);
    setFormData({
      name: "",
      phone: "",
      email: "",
      department: "",
    });
  };

  // Render loading, error, and main content
  if (loading)
    return (
      <div className="flex items-center justify-center min-h-screen">
        Loading fixers...
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
          <li className="mb-2">
            <a href="/users" className="hover:text-gray-300">
              Approvers
            </a>
          </li>
          <li className="mb-2">
            <a href="/fixers" className="hover:text-gray-300">
              Engineers
            </a>
          </li>
        </ul>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Engineers</h1>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Create Fixer
          </button>
        </div>

        {/* Fixers Table */}
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="p-3 bg-gray-100">
            <h2 className="text-xl font-semibold">All Fixers</h2>
          </div>
          <div className="overflow-x-auto max-h-[calc(100vh-490px)] overflow-y-auto">
            <table className="w-full table-fixed">
              <thead className="bg-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left w-1/6">ID</th>
                  <th className="px-4 py-2 text-left w-2/6">Name</th>
                  <th className="px-4 py-2 text-left w-2/6">Email</th>
                  <th className="px-4 py-2 text-left w-1/6">Phone</th>
                  <th className="px-4 py-2 text-left w-1/6">Department</th>
                </tr>
              </thead>
              <tbody>
                {fixers.map((fixer) => (
                  <tr
                    key={fixer.id}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleRowClick(fixer)}
                  >
                    <td className="px-4 py-2 truncate">{fixer.id}</td>
                    <td className="px-4 py-2 truncate">{fixer.name}</td>
                    <td className="px-4 py-2 truncate">{fixer.email}</td>
                    <td className="px-4 py-2 truncate">{fixer.phone || "-"}</td>
                    <td className="px-4 py-2 truncate">
                      {fixer.department || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create Fixer Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-lg shadow-lg max-w-2xl w-full mx-4 max-h-[100vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Create New Fixer</h2>
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
                      Name
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
                      Phone
                    </label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleFormChange}
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
                      Department
                    </label>
                    <select
                      name="department"
                      value={formData.department}
                      onChange={handleFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select Department</option>
                      <option value="IT">IT</option>
                      <option value="HR">HR</option>
                      <option value="Finance">Finance</option>
                      <option value="Operations">Operations</option>
                    </select>
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
                    Create Fixer
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Fixer Modal */}
        {showEditModal && selectedFixer && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <h2 className="text-2xl font-bold mb-6">Edit Fixer</h2>
              <form onSubmit={handleEditFormSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Name
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
                      Phone
                    </label>
                    <input
                      type="tel"
                      name="phone"
                      value={editFormData.phone}
                      onChange={handleEditFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="md:col-span-2">
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
                      Department
                    </label>
                    <select
                      name="department"
                      value={editFormData.department}
                      onChange={handleEditFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Select Department</option>
                      <option value="IT">IT</option>
                      <option value="HR">HR</option>
                      <option value="Finance">Finance</option>
                      <option value="Operations">Operations</option>
                    </select>
                  </div>
                </div>

                <div className="flex justify-between space-x-4 mt-6">
                  <button
                    type="button"
                    onClick={handleDeleteFixer}
                    className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    Delete Fixer
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
                      Update Fixer
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

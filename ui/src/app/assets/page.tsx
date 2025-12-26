"use client";

import { useEffect, useState, useMemo } from "react";
import Select from "react-select";

interface Asset {
  id: number;
  date: string;
  created_by: string;
  action: string;
  item: string;
  serial_number?: string;
  target: string;
  checked_out?: boolean;
  checked_out_time?: string;
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [formData, setFormData] = useState<{
    action: string;
    item: string;
    serial_number: string;
    target: string;
  }>({
    action: "",
    item: "",
    serial_number: "",
    target: "",
  });
  const [editFormData, setEditFormData] = useState<{
    action: string;
    item: string;
    serial_number: string;
    target: string;
  }>({
    action: "",
    item: "",
    serial_number: "",
    target: "",
  });

  const [user, setUser] = useState<any>(null);

  const [createLoading, setCreateLoading] = useState(false);

  // Check if create form is valid (all fields must be filled)
  const isCreateFormValid = useMemo(() => {
    return (
      formData.action.trim() !== "" &&
      formData.item.trim() !== "" &&
      formData.serial_number.trim() !== "" &&
      formData.target.trim() !== ""
    );
  }, [formData]);

  // Check if edit form is valid (all fields must be filled)
  const isEditFormValid = useMemo(() => {
    return (
      editFormData.action.trim() !== "" &&
      editFormData.item.trim() !== "" &&
      editFormData.serial_number.trim() !== "" &&
      editFormData.target.trim() !== ""
    );
  }, [editFormData]);

  // Fetch assets on component mount
  useEffect(() => {
    fetchAssets();
  }, []);

  // Fetch current user
  useEffect(() => {
    fetch("http://localhost:8000/auth/me", { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setUser(data))
      .catch(() => setUser(null));
  }, []);

  // Function to fetch assets from backend
  const fetchAssets = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/assets", {
        credentials: "include",
      });
      const data = await response.json();
      if (response.ok) {
        setAssets(data.assets || []);
      } else {
        setError(data.error || "Failed to fetch assets");
      }
    } catch (err) {
      setError("Failed to fetch assets");
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

  // Handle form submission for creating a new asset
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setCreateLoading(true);
    try {
      const response = await fetch("http://localhost:8000/assets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          ...formData,
          created_by: user?.username || "Unknown",
        }),
      });
      const data = await response.json();
      if (response.ok) {
        setFormData({
          action: "",
          item: "",
          serial_number: "",
          target: "",
        });
        // Refresh assets list
        fetchAssets();
        setShowCreateModal(false);
      } else {
        alert(data.error || "Failed to create asset");
      }
    } catch (error) {
      alert("Failed to create asset");
    } finally {
      setCreateLoading(false);
    }
  };

  // Handle row click to open edit modal
  const handleRowClick = (asset: Asset) => {
    setSelectedAsset(asset);
    setEditFormData({
      action: asset.action,
      item: asset.item,
      serial_number: asset.serial_number || "",
      target: asset.target,
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
    if (!selectedAsset) return;

    try {
      const response = await fetch(
        `http://localhost:8000/assets/${selectedAsset.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify(editFormData),
        }
      );
      const data = await response.json();
      if (response.ok) {
        fetchAssets();
        setShowEditModal(false);
      } else {
        alert(data.error || "Failed to update asset");
      }
    } catch (error) {
      alert("Failed to update asset");
    }
  };

  // Handle checkout
  const handleCheckout = async () => {
    if (!selectedAsset) return;

    try {
      // First, update the original asset to checked_out = true
      const updateResponse = await fetch(
        `http://localhost:8000/assets/${selectedAsset.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({
            checked_out: true,
          }),
        }
      );

      if (!updateResponse.ok) {
        const updateData = await updateResponse.json();
        alert(updateData.error || "Failed to update asset status");
        return;
      }

      // Update the local selectedAsset to reflect the change immediately
      const checkoutTime = new Date().toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
      setSelectedAsset({
        ...selectedAsset,
        checked_out: true,
        checked_out_time: checkoutTime,
      });

      // Then, create the Check Out entry
      const response = await fetch("http://localhost:8000/assets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          action: "Check Out",
          item: selectedAsset.item,
          serial_number: selectedAsset.serial_number || "",
          target: selectedAsset.target,
          created_by: user?.username || "Unknown",
        }),
      });
      const data = await response.json();
      if (response.ok) {
        fetchAssets();
        closeEditModal();
      } else {
        alert(data.error || "Failed to record checkout");
      }
    } catch (error) {
      alert("Failed to record checkout");
    }
  };

  // Handle asset deletion
  const handleDeleteAsset = async () => {
    if (!selectedAsset) return;

    if (!confirm(`Are you sure you want to delete this asset entry?`)) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8000/assets/${selectedAsset.id}`,
        {
          method: "DELETE",
          credentials: "include",
        }
      );
      const data = await response.json();
      if (response.ok && !data.error) {
        fetchAssets();
        setShowEditModal(false);
      } else {
        alert(data.error || "Failed to delete asset");
      }
    } catch (error) {
      alert("Failed to delete asset");
    }
  };

  // Close edit modal
  const closeEditModal = () => {
    setShowEditModal(false);
    setSelectedAsset(null);
    setEditFormData({
      action: "",
      item: "",
      serial_number: "",
      target: "",
    });
  };

  // Close create modal
  const closeCreateModal = () => {
    setShowCreateModal(false);
    setFormData({
      action: "",
      item: "",
      serial_number: "",
      target: "",
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
        Loading assets...
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
          <h1 className="text-3xl font-bold">Asset Management</h1>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Create Asset
          </button>
        </div>

        {/* Assets Table */}
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="p-3 bg-gray-100">
            <h2 className="text-xl font-semibold">All Assets</h2>
          </div>
          <div className="overflow-x-auto max-h-[calc(100vh-490px)] overflow-y-auto">
            <table className="w-full table-fixed">
              <thead className="bg-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left w-1/7">ID</th>
                  <th className="px-4 py-2 text-left w-1/7">Date</th>
                  <th className="px-4 py-2 text-left w-1/7">Created By</th>
                  <th className="px-4 py-2 text-left w-1/7">Action</th>
                  <th className="px-4 py-2 text-left w-1/7">Item</th>
                  <th className="px-4 py-2 text-left w-1/7">Serial Number</th>
                  <th className="px-4 py-2 text-left w-1/7">Target</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr
                    key={asset.id}
                    className="border-t hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleRowClick(asset)}
                  >
                    <td className="px-4 py-2 truncate">{asset.id}</td>
                    <td className="px-4 py-2 truncate">
                      {(() => {
                        const date = new Date(asset.date);
                        return `${date.toLocaleDateString("en-GB", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "2-digit",
                        })} ${date.toLocaleTimeString("en-GB", {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                          hour12: false,
                        })}`;
                      })()}
                    </td>
                    <td className="px-4 py-2 truncate">{asset.created_by}</td>
                    <td className="px-4 py-2 truncate">{asset.action}</td>
                    <td className="px-4 py-2 truncate">{asset.item}</td>
                    <td className="px-4 py-2 truncate">
                      {asset.serial_number || ""}
                    </td>
                    <td className="px-4 py-2 truncate">{asset.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create Asset Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-lg shadow-lg max-w-2xl w-full mx-4 min-h-[20vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">Create New Asset</h2>
                <button
                  onClick={closeCreateModal}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>

              <form onSubmit={handleFormSubmit}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Action
                    </label>
                    <Select
                      options={[
                        { value: "Check In", label: "Check In" },
                        { value: "Transfer", label: "Transfer" },
                        { value: "Maintenance", label: "Maintenance" },
                      ]}
                      value={
                        formData.action
                          ? { value: formData.action, label: formData.action }
                          : null
                      }
                      onChange={(selected) =>
                        setFormData({
                          ...formData,
                          action: selected ? selected.value : "",
                        })
                      }
                      placeholder="Select Action"
                      maxMenuHeight={120}
                      styles={{
                        control: (provided) => ({
                          ...provided,
                          border: "1px solid #d1d5db",
                          borderRadius: "0.375rem",
                          padding: "0.125rem",
                          fontSize: "0.875rem",
                          minHeight: "2.5rem",
                        }),
                        menu: (provided) => ({
                          ...provided,
                          fontSize: "0.875rem",
                        }),
                      }}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Item
                    </label>
                    <input
                      type="text"
                      name="item"
                      value={formData.item}
                      onChange={handleFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Serial Number
                    </label>
                    <input
                      type="text"
                      name="serial_number"
                      value={formData.serial_number}
                      onChange={handleFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Target
                    </label>
                    <input
                      type="text"
                      name="target"
                      value={formData.target}
                      onChange={handleFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="flex justify-end space-x-4 mt-12">
                  <button
                    type="button"
                    onClick={closeCreateModal}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!isCreateFormValid || createLoading}
                    className={`px-4 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      isCreateFormValid && !createLoading
                        ? "bg-blue-600 text-white hover:bg-blue-700"
                        : "bg-gray-400 text-gray-200 cursor-not-allowed"
                    }`}
                  >
                    {createLoading ? "Creating..." : "Create"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Asset Modal */}
        {showEditModal && selectedAsset && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white p-6 rounded-lg shadow-lg max-w-2xl w-full mx-4 min-h-[20vh] overflow-y-auto">
              <h2 className="text-2xl font-bold mb-6">Edit Asset</h2>
              <form onSubmit={handleEditFormSubmit}>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Action
                    </label>
                    <Select
                      options={[
                        { value: "Check In", label: "Check In" },
                        { value: "Transfer", label: "Transfer" },
                        { value: "Maintenance", label: "Maintenance" },
                      ]}
                      value={
                        editFormData.action
                          ? {
                              value: editFormData.action,
                              label: editFormData.action,
                            }
                          : null
                      }
                      onChange={(selected) =>
                        setEditFormData({
                          ...editFormData,
                          action: selected ? selected.value : "",
                        })
                      }
                      placeholder="Select Action"
                      maxMenuHeight={120}
                      styles={{
                        control: (provided) => ({
                          ...provided,
                          border: "1px solid #d1d5db",
                          borderRadius: "0.375rem",
                          padding: "0.125rem",
                          fontSize: "0.875rem",
                          minHeight: "2.5rem",
                        }),
                        menu: (provided) => ({
                          ...provided,
                          fontSize: "0.875rem",
                        }),
                      }}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Item
                    </label>
                    <input
                      type="text"
                      name="item"
                      value={editFormData.item}
                      onChange={handleEditFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Serial Number
                    </label>
                    <input
                      type="text"
                      name="serial_number"
                      value={editFormData.serial_number}
                      onChange={handleEditFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Target
                    </label>
                    <input
                      type="text"
                      name="target"
                      value={editFormData.target}
                      onChange={handleEditFormChange}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center mt-12">
                  <div className="flex space-x-4">
                    <button
                      type="button"
                      onClick={handleDeleteAsset}
                      className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                    >
                      Delete
                    </button>
                    {selectedAsset?.action === "Check In" && (
                      <button
                        type="button"
                        onClick={handleCheckout}
                        disabled={selectedAsset?.checked_out === true}
                        className={`px-4 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 ${
                          selectedAsset?.checked_out === true
                            ? "bg-gray-400 text-gray-200 cursor-not-allowed"
                            : "bg-green-600 text-white hover:bg-green-700"
                        }`}
                      >
                        {selectedAsset?.checked_out === true
                          ? `Checked Out (${
                              selectedAsset?.checked_out_time
                                ? (() => {
                                    const date = new Date(
                                      selectedAsset.checked_out_time
                                    );
                                    const dateStr = date.toLocaleDateString(
                                      "en-GB",
                                      {
                                        day: "2-digit",
                                        month: "2-digit",
                                        year: "2-digit",
                                        timeZone: "Asia/Singapore",
                                      }
                                    );
                                    const timeStr = date.toLocaleTimeString(
                                      "en-GB",
                                      {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                        second: "2-digit",
                                        hour12: false,
                                        timeZone: "Asia/Singapore",
                                      }
                                    );
                                    return `${dateStr} ${timeStr}`;
                                  })()
                                : "N/A"
                            })`
                          : "Checkout"}
                      </button>
                    )}
                  </div>
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
                      Update
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

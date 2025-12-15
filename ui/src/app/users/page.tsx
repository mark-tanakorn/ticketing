'use client';

import { useEffect, useState, useMemo } from 'react';

interface User {
  id: number;
  name: string;
  phone: string;
  email: string;
  department: string;
  approval_tier: number;
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    department: '',
    approval_tier: '1'
  });
  const [editFormData, setEditFormData] = useState({
    name: '',
    phone: '',
    email: '',
    department: '',
    approval_tier: '1'
  });

  // Check if create form is valid (all fields must be filled)
  const isCreateFormValid = useMemo(() => {
    return formData.name.trim() !== '' &&
           formData.phone.trim() !== '' &&
           formData.email.trim() !== '' &&
           formData.department !== '' &&
           formData.approval_tier !== '';
  }, [formData]);

  // Check if edit form is valid (all fields must be filled)
  const isEditFormValid = useMemo(() => {
    return editFormData.name.trim() !== '' &&
           editFormData.phone.trim() !== '' &&
           editFormData.email.trim() !== '' &&
           editFormData.department !== '' &&
           editFormData.approval_tier !== '';
  }, [editFormData]);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/users');
      const data = await response.json();
      if (response.ok) {
        setUsers(data.users || []);
      } else {
        setError(data.error || 'Failed to fetch users');
      }
    } catch (err) {
      setError('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check for duplicate email
    const existingUser = users.find(u => u.email === formData.email);
    if (existingUser) {
      alert('A user with this email already exists.');
      return;
    }
    
    try {
      const response = await fetch('http://localhost:8000/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: formData.name,
          phone: formData.phone,
          email: formData.email,
          department: formData.department,
          approval_tier: parseInt(formData.approval_tier)
        })
      });
      const data = await response.json();
      if (response.ok) {
        setFormData({
          name: '',
          phone: '',
          email: '',
          department: '',
          approval_tier: '1'
        });
        // Refresh users list
        fetchUsers();
        setShowCreateModal(false);
      } else {
        // Error handled silently
      }
    } catch (error) {
      // Error handled silently
    }
  };

  const handleRowClick = (user: User) => {
    setSelectedUser(user);
    setEditFormData({
      name: user.name,
      phone: user.phone || '',
      email: user.email,
      department: user.department || '',
      approval_tier: user.approval_tier.toString()
    });
    setShowEditModal(true);
  };

  const handleEditFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setEditFormData({
      ...editFormData,
      [e.target.name]: e.target.value
    });
  };

  const handleEditFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    // Check for duplicate email (excluding current user)
    const existingUser = users.find(u => u.email === editFormData.email && u.id !== selectedUser.id);
    if (existingUser) {
      alert('Another user with this email already exists.');
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: editFormData.name,
          phone: editFormData.phone,
          email: editFormData.email,
          department: editFormData.department,
          approval_tier: parseInt(editFormData.approval_tier)
        })
      });
      const data = await response.json();
      if (response.ok) {
        fetchUsers();
        setShowEditModal(false);
      } else {
        // Error handled silently
      }
    } catch (error) {
      // Error handled silently
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;

    if (!confirm(`Are you sure you want to delete ${selectedUser.name}?`)) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/users/${selectedUser.id}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      if (response.ok) {
        fetchUsers();
        setShowEditModal(false);
      } else {
        // Error handled silently
      }
    } catch (error) {
      // Error handled silently
    }
  };

  const closeEditModal = () => {
    setShowEditModal(false);
    setSelectedUser(null);
    setEditFormData({
      name: '',
      phone: '',
      email: '',
      department: '',
      approval_tier: '1'
    });
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setFormData({
      name: '',
      phone: '',
      email: '',
      department: '',
      approval_tier: '1'
    });
  };

  if (loading) return <div className="flex items-center justify-center min-h-screen">Loading users...</div>;
  if (error) return <div className="flex items-center justify-center min-h-screen text-red-600">Error: {error}</div>;

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 text-white p-4">
        <h2 className="text-xl font-bold mb-4">Navigation</h2>
        <ul>
          <li className="mb-2"><a href="/" className="hover:text-gray-300">Dashboard</a></li>
          <li className="mb-2"><a href="/users" className="hover:text-gray-300">Users</a></li>
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
          <div className="overflow-x-auto max-h-[calc(100vh-470px)] overflow-y-auto">
            <table className="w-full table-fixed">
              <thead className="bg-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left w-1/6">ID</th>
                  <th className="px-4 py-2 text-left w-2/6">Name</th>
                  <th className="px-4 py-2 text-left w-2/6">Email</th>
                  <th className="px-4 py-2 text-left w-1/6">Phone</th>
                  <th className="px-4 py-2 text-left w-1/6">Department</th>
                  <th className="px-4 py-2 text-left w-1/6">Approval Tier</th>
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
                    <td className="px-4 py-2 truncate">{user.phone || '-'}</td>
                    <td className="px-4 py-2 truncate">{user.department || '-'}</td>
                    <td className="px-4 py-2 truncate">{user.approval_tier || '-'}</td>
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
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
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
                    <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone}
                      onChange={handleFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
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
                    <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
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

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Approval Tier</label>
                    <select
                      name="approval_tier"
                      value={formData.approval_tier}
                      onChange={handleFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="3">3</option>
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
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-gray-400 text-gray-200 cursor-not-allowed'
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
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
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
                    <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                    <input
                      type="tel"
                      name="phone"
                      value={editFormData.phone}
                      onChange={handleEditFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
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
                    <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
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

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Approval Tier</label>
                    <select
                      name="approval_tier"
                      value={editFormData.approval_tier}
                      onChange={handleEditFormChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="3">3</option>
                    </select>
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
                          ? 'bg-blue-600 text-white hover:bg-blue-700'
                          : 'bg-gray-400 text-gray-200 cursor-not-allowed'
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
'use client';

export default function Users() {
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
        <h1 className="text-3xl font-bold mb-6">Users</h1>

        {/* Empty page content */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <p className="text-gray-600">Users page content will go here.</p>
        </div>
      </div>
    </div>
  );
}
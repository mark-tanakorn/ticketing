'use client';

import { useEffect, useState, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const getSeverityColor = (severity: string) => {
  switch (severity.toLowerCase()) {
    case 'critical': return '#8B0000';
    case 'high': return '#E60000';
    case 'medium': return '#FF7800';
    case 'low': return '#4CBB17';
    default: return '#8884d8';
  }
};

const getStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'closed': return '#AAAAAA';
    case 'open': return '#4CBB17';
    case 'in_progress':
    case 'in progress': return '#45B6FE';
    case 'awaiting_approval':
    case 'awaiting approval': return '#FF7800';
    case 'approval_denied':
    case 'approval denied': return '#E60000';
    case 'sla_breached':
    case 'sla breached': return '#8B0000';
    
    default: return '#8884d8';
  }
};

const formatter = (name: string) => name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()).replace(/\bSla\b/g, 'SLA');

const CustomLegend = ({ payload, order }: { payload?: readonly any[], order: string[] }) => {
  const sortedPayload = (payload || []).slice().sort((a, b) => order.indexOf(a.value) - order.indexOf(b.value));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
      {sortedPayload.map((entry, index) => (
        <div key={`legend-${index}`} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
          <div style={{ width: 10, height: 10, backgroundColor: entry.color, borderRadius: '50%', marginRight: 8 }}></div>
          <span>{entry.value}</span>
        </div>
      ))}
    </div>
  );
};

const renderCustomLabel = ({ cx, cy, midAngle = 0, innerRadius, outerRadius, value }: { cx: any; cy: any; midAngle?: any; innerRadius: any; outerRadius: any; value: any; }) => {
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="middle" fontSize={16} fontWeight="bold">
      {value}
    </text>
  );
};

interface Ticket {
  id: number;
  title: string;
  description: string;
  category: string;
  severity: string;
  date_created: string;
  status: string;
  attachment_upload: string;
  approver: string;
  fixer: string;
}

export default function Home() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortConfig, setSortConfig] = useState<{ column: keyof Ticket | 'pic' | null; direction: 'asc' | 'desc' }>({ column: null, direction: 'asc' });
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    severity: 'low',
    department: '',
    status: 'open',
    approval_tier: '1',
    assigned_to: '',
    attachment_upload: ''
  });
  const [message, setMessage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchColumns, setSearchColumns] = useState<(keyof Ticket | 'pic')[]>(['title', 'description', 'category', 'severity', 'status', 'pic']);

  useEffect(() => {
    fetch('http://localhost:8000/tickets')
      .then((res) => res.json())
      .then((data) => {
        setTickets(data.tickets || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching tickets:', err);
        setTickets([]);
        setLoading(false);
      });
  }, []);

  const filteredAndSortedTickets = useMemo(() => {
    // First filter by search term
    let filtered = tickets;
    if (searchTerm) {
      filtered = tickets.filter(ticket => {
        return searchColumns.some(column => {
          if (column === 'pic') {
            const status = ticket.status.toLowerCase();
            let picValue = '';
            if (['closed', 'open', 'in_progress', 'in progress', 'sla_breached', 'sla breached'].includes(status)) {
              picValue = ticket.fixer || '';
            } else if (['awaiting_approval', 'awaiting approval', 'approval_denied', 'approval denied'].includes(status)) {
              picValue = ticket.approver || '';
            }
            return picValue.toLowerCase().includes(searchTerm.toLowerCase());
          }
          const value = ticket[column as keyof Ticket];
          return value && value.toString().toLowerCase().includes(searchTerm.toLowerCase());
        });
      });
    }

    // Then sort
    if (!sortConfig.column) return filtered;
    return [...filtered].sort((a, b) => {
      let aValue: any;
      let bValue: any;

      if (sortConfig.column === 'pic') {
        const getPic = (ticket: Ticket) => {
          const status = ticket.status.toLowerCase();
          if (['closed', 'open', 'in_progress', 'in progress', 'sla_breached', 'sla breached'].includes(status)) {
            return ticket.fixer || '';
          } else if (['awaiting_approval', 'awaiting approval', 'approval_denied', 'approval denied'].includes(status)) {
            return ticket.approver || '';
          }
          return '';
        };
        aValue = getPic(a).toLowerCase();
        bValue = getPic(b).toLowerCase();
      } else {
        aValue = a[sortConfig.column as keyof Ticket];
        bValue = b[sortConfig.column as keyof Ticket];
      }

      if (sortConfig.column === 'date_created') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [tickets, sortConfig, searchTerm, searchColumns]);

  const handleSort = (column: keyof Ticket | 'pic') => {
    setSortConfig(prev => {
      if (prev.column === column) {
        // Toggle direction
        return {
          column,
          direction: prev.direction === 'asc' ? 'desc' : 'asc'
        };
      } else {
        // New column, set default direction
        const defaultDirection = column === 'status' ? 'desc' : 'asc';
        return {
          column,
          direction: defaultDirection
        };
      }
    });
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type, files } = e.target as HTMLInputElement;
    if (type === 'file' && files) {
      setFormData({
        ...formData,
        [name]: files[0]?.name || ''
      });
    } else {
      let newFormData = {
        ...formData,
        [name]: value
      };
      
      // Reset approval_tier if department is cleared
      if (name === 'department' && !value) {
        newFormData.approval_tier = '1';
      }
      
      setFormData(newFormData);
    }
  };

  const clearAttachment = () => {
    setFormData({
      ...formData,
      attachment_upload: ''
    });
    // Also clear the file input
    const fileInput = document.querySelector('input[name="attachment_upload"]') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      if (response.ok) {
        setMessage('Ticket created successfully!');
        setFormData({
          title: '',
          description: '',
          category: '',
          severity: 'low',
          department: '',
          status: 'open',
          approval_tier: '1',
          assigned_to: '',
          attachment_upload: ''
        });
        // Refresh tickets data
        fetch('http://localhost:8000/tickets')
          .then((res) => res.json())
          .then((data) => {
            setTickets(data.tickets || []);
          })
          .catch((err) => console.error('Error refreshing tickets:', err));
        setShowCreateModal(false);
      } else {
        setMessage(`Error: ${data.error}`);
      }
    } catch (error) {
      setMessage('Error creating ticket');
    }
  };

  const chartData = useMemo(() => {
    if (!tickets || !tickets.length) return { severity: [], status: [], monthly: [] };

    // Severity counts
    const severityCount: { [key: string]: number } = {};
    tickets.forEach(ticket => {
      severityCount[ticket.severity] = (severityCount[ticket.severity] || 0) + 1;
    });
    const severityOrder = { 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
    const severity = Object.entries(severityCount).map(([name, value]) => ({ name: formatter(name), value })).sort((a, b) => (severityOrder[b.name as keyof typeof severityOrder] || 99) - (severityOrder[a.name as keyof typeof severityOrder] || 99));

    // Status counts
    const statusCount: { [key: string]: number } = {};
    tickets.forEach(ticket => {
      statusCount[ticket.status] = (statusCount[ticket.status] || 0) + 1;
    });
    const statusOrder = { 'SLA Breached': 1, 'Open': 2, 'In Progress': 3, 'Awaiting Approval': 4, 'Approval Denied': 5, 'Closed': 6 };
    const status = Object.entries(statusCount).map(([name, value]) => ({ name: formatter(name), value })).sort((a, b) => (statusOrder[a.name as keyof typeof statusOrder] || 99) - (statusOrder[b.name as keyof typeof statusOrder] || 99));

    // Monthly counts
    const monthlyCount: { [key: string]: number } = {};
    tickets.forEach(ticket => {
      const month = new Date(ticket.date_created).toLocaleString('default', { month: 'short', year: '2-digit' });
      monthlyCount[month] = (monthlyCount[month] || 0) + 1;
    });
    const monthly = Object.entries(monthlyCount).map(([name, value]) => ({ name, value })).sort((a, b) => {
      const dateA = new Date(a.name.replace(/(\w{3}) (\d{2})/, '$1 20$2'));
      const dateB = new Date(b.name.replace(/(\w{3}) (\d{2})/, '$1 20$2'));
      return dateA.getTime() - dateB.getTime();
    });

    return { severity, status, monthly };
  }, [tickets]);

  if (loading) return <div className="flex items-center justify-center min-h-screen">Loading tickets...</div>;

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 text-white p-4">
        <h2 className="text-xl font-bold mb-4">Navigation</h2>
        <ul>
          <li className="mb-2"><a href="#" className="hover:text-gray-300">Dashboard</a></li>
          <li className="mb-2">
            <button
              onClick={() => setShowCreateModal(true)}
              className="hover:text-gray-300 text-left w-full"
            >
              Tickets
            </button>
          </li>
          <li className="mb-2"><a href="#" className="hover:text-gray-300">Reports</a></li>
          <li className="mb-2"><a href="#" className="hover:text-gray-300">Settings</a></li>
        </ul>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <h1 className="text-3xl font-bold mb-6">Ticketing System Dashboard</h1>

        {/* Cards with Charts */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {/* Severity Chart */}
          <div className="bg-white p-4 rounded-lg shadow-md md:col-span-1">
            <h3 className="text-lg font-semibold mb-2 text-center">Tickets by Severity</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={chartData.severity} cx="50%" cy="49%" outerRadius={80} fill="#8884d8" dataKey="value" label={renderCustomLabel} labelLine={false}>
                  {chartData.severity.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getSeverityColor(entry.name)} />
                  ))}
                </Pie>
                <Legend content={(props) => <CustomLegend {...props} order={['Critical', 'High', 'Medium', 'Low']} />} layout="vertical" verticalAlign="middle" align="right" iconType="circle" wrapperStyle={{ transform: 'translateX(-20px)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Status Chart */}
          <div className="bg-white p-4 rounded-lg shadow-md md:col-span-1">
            <h3 className="text-lg font-semibold mb-2 text-center">Tickets by Status</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={chartData.status} cx="50%" cy="49%" outerRadius={80} fill="#8884d8" dataKey="value" label={renderCustomLabel} labelLine={false}>
                  {chartData.status.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getStatusColor(entry.name)} />
                  ))}
                </Pie>
                <Legend content={(props) => <CustomLegend {...props} order={['SLA Breached', 'Open', 'In Progress', 'Awaiting Approval', 'Approval Denied', 'Closed']} />} layout="vertical" verticalAlign="middle" align="right" iconType="circle" wrapperStyle={{ transform: 'translateX(-5px)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Monthly Chart */}
          <div className="bg-white p-4 rounded-lg shadow-md md:col-span-2">
            <h3 className="text-lg font-semibold mb-2 text-center">Tickets Created per Month</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData.monthly}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#8884d8" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tickets Table */}
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="p-3 bg-gray-100">
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
              <h2 className="text-xl font-semibold">All Tickets</h2>
              <div className="flex flex-col lg:flex-row gap-3 w-full lg:w-auto lg:min-w-[600px] lg:items-center">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search tickets..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="px-4 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm lg:w-170 mr-3"
                  />
                  {searchTerm && (
                    <button
                      onClick={() => setSearchTerm('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none mr-3"
                      type="button"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-3 text-sm">
                  <label className="flex items-center mr-1">
                    <input
                      type="checkbox"
                      checked={searchColumns.includes('title')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSearchColumns([...searchColumns, 'title']);
                        } else {
                          setSearchColumns(searchColumns.filter(col => col !== 'title'));
                        }
                      }}
                      className="mr-1"
                    />
                    Title
                  </label>
                  <label className="flex items-center mr-1">
                    <input
                      type="checkbox"
                      checked={searchColumns.includes('description')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSearchColumns([...searchColumns, 'description']);
                        } else {
                          setSearchColumns(searchColumns.filter(col => col !== 'description'));
                        }
                      }}
                      className="mr-1"
                    />
                    Description
                  </label>
                  <label className="flex items-center mr-1">
                    <input
                      type="checkbox"
                      checked={searchColumns.includes('category')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSearchColumns([...searchColumns, 'category']);
                        } else {
                          setSearchColumns(searchColumns.filter(col => col !== 'category'));
                        }
                      }}
                      className="mr-1"
                    />
                    Category
                  </label>
                  <label className="flex items-center mr-1">
                    <input
                      type="checkbox"
                      checked={searchColumns.includes('severity')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSearchColumns([...searchColumns, 'severity']);
                        } else {
                          setSearchColumns(searchColumns.filter(col => col !== 'severity'));
                        }
                      }}
                      className="mr-1"
                    />
                    Severity
                  </label>
                  <label className="flex items-center mr-1">
                    <input
                      type="checkbox"
                      checked={searchColumns.includes('status')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSearchColumns([...searchColumns, 'status']);
                        } else {
                          setSearchColumns(searchColumns.filter(col => col !== 'status'));
                        }
                      }}
                      className="mr-1"
                    />
                    Status
                  </label>
                  <label className="flex items-center mr-3">
                    <input
                      type="checkbox"
                      checked={searchColumns.includes('pic')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSearchColumns([...searchColumns, 'pic']);
                        } else {
                          setSearchColumns(searchColumns.filter(col => col !== 'pic'));
                        }
                      }}
                      className="mr-1"
                    />
                    PIC
                  </label>
                </div>
              </div>
            </div>
          </div>
          <div className="overflow-x-auto max-h-128 overflow-y-auto">
            <table className="w-full table-fixed">
              <thead className="bg-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left w-2/22">ID</th>
                  <th className="px-4 py-2 text-left w-3/22">Title</th>
                  <th className="px-4 py-2 text-left w-5/22">Description</th>
                  <th className="px-4 py-2 text-left cursor-pointer w-2/22" onClick={() => handleSort('category')}>Category <span style={{ color: sortConfig.column === 'category' ? 'red' : 'grey', fontWeight: sortConfig.column === 'category' ? 'bolder' : 'normal' }}>{sortConfig.column === 'category' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer w-2/22" onClick={() => handleSort('severity')}>Severity <span style={{ color: sortConfig.column === 'severity' ? 'red' : 'grey', fontWeight: sortConfig.column === 'severity' ? 'bolder' : 'normal' }}>{sortConfig.column === 'severity' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer w-2/22" onClick={() => handleSort('status')}>Status <span style={{ color: sortConfig.column === 'status' ? 'red' : 'grey', fontWeight: sortConfig.column === 'status' ? 'bolder' : 'normal' }}>{sortConfig.column === 'status' ? (sortConfig.direction === 'desc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer w-2/22" onClick={() => handleSort('pic')}>PIC <span style={{ color: sortConfig.column === 'pic' ? 'red' : 'grey', fontWeight: sortConfig.column === 'pic' ? 'bolder' : 'normal' }}>{sortConfig.column === 'pic' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer w-2/22" onClick={() => handleSort('date_created')}>Date Created <span style={{ color: sortConfig.column === 'date_created' ? 'red' : 'grey', fontWeight: sortConfig.column === 'date_created' ? 'bolder' : 'normal' }}>{sortConfig.column === 'date_created' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left w-2/22">Attachments</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedTickets.map((ticket) => (
                  <tr key={ticket.id} className="border-t">
                    <td className="px-4 py-2 truncate">{ticket.id}</td>
                    <td className="px-4 py-2 truncate">{ticket.title}</td>
                    <td className="px-4 py-2 truncate" title={ticket.description}>{ticket.description}</td>
                    <td className="px-4 py-2 truncate">{ticket.category}</td>
                    <td className="px-4 py-2 truncate" style={{ color: getSeverityColor(ticket.severity) }}>{formatter(ticket.severity)}</td>
                    <td className="px-4 py-2 truncate" style={{ color: getStatusColor(ticket.status) }}>{formatter(ticket.status)}</td>
                    <td className="px-4 py-2 truncate">{(() => {
                      const status = ticket.status.toLowerCase();
                      if (['closed', 'open', 'in_progress', 'in progress', 'sla_breached', 'sla breached'].includes(status)) {
                        return ticket.fixer || '';
                      } else if (['awaiting_approval', 'awaiting approval', 'approval_denied', 'approval denied'].includes(status)) {
                        return ticket.approver || '';
                      }
                      return '';
                    })()}</td>
                    <td className="px-4 py-2 truncate">{(() => {
                      const date = new Date(ticket.date_created);
                      return date.toLocaleString('en-US', {
                        month: '2-digit',
                        day: '2-digit',
                        year: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false
                      });
                    })()}</td>
                    <td className="px-4 py-2 truncate" title={ticket.attachment_upload || ''}>{ticket.attachment_upload || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Create Ticket Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-4xl w-full mx-4 max-h-[100vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">Create New Ticket</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleFormChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    name="category"
                    value={formData.category}
                    onChange={handleFormChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select Category</option>
                    <option value="Network">Network</option>
                    <option value="Hardware">Hardware</option>
                    <option value="Access">Access</option>
                    <option value="Software">Software</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
                  <select
                    name="severity"
                    value={formData.severity}
                    onChange={handleFormChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
                  <select
                    name="department"
                    value={formData.department || ''}
                    onChange={handleFormChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select Department</option>
                    <option value="IT">IT</option>
                    <option value="HR">HR</option>
                    <option value="Finance">Finance</option>
                    <option value="Operations">Operations</option>
                    <option value="Legal">Legal</option>
                    <option value="Marketing">Marketing</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Approval Tier</label>
                  <select
                    name="approval_tier"
                    value={formData.approval_tier}
                    onChange={handleFormChange}
                    disabled={!formData.department}
                    className={`w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      !formData.department ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''
                    }`}
                  >
                    <option value="1">Tier 1</option>
                    <option value="2">Tier 2</option>
                    <option value="3">Tier 3</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Assign To</label>
                  <input
                    type="text"
                    name="assigned_to"
                    value={formData.assigned_to}
                    onChange={handleFormChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="md:col-span-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Attachment Upload</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="file"
                      name="attachment_upload"
                      onChange={handleFormChange}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    {formData.attachment_upload && (
                      <button
                        type="button"
                        onClick={clearAttachment}
                        className="px-3 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500"
                        title="Remove attachment"
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleFormChange}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex justify-end space-x-4 mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Create Ticket
                </button>
              </div>

              {message && (
                <p className={`mt-4 ${message.includes('Error') ? 'text-red-600' : 'text-green-600'}`}>
                  {message}
                </p>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

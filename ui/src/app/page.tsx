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
    default: return '#8884d8';
  }
};

const formatter = (name: string) => name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

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
  assigned_to: string;
  attachment_upload: string;
}

export default function Home() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortConfig, setSortConfig] = useState<{ column: keyof Ticket | null; direction: 'asc' | 'desc' }>({ column: null, direction: 'asc' });

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

  const sortedTickets = useMemo(() => {
    if (!sortConfig.column) return tickets;
    return [...tickets].sort((a, b) => {
      let aValue: any = a[sortConfig.column!];
      let bValue: any = b[sortConfig.column!];
      if (sortConfig.column === 'date_created') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }
      if (sortConfig.column === 'severity') {
        const severityOrder = { 'low': 4, 'medium': 3, 'high': 2, 'critical': 1 };
        aValue = severityOrder[aValue.toLowerCase() as keyof typeof severityOrder] || 99;
        bValue = severityOrder[bValue.toLowerCase() as keyof typeof severityOrder] || 99;
      }
      if (sortConfig.column === 'category') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }
      if (sortConfig.column === 'status') {
        const statusOrder = { 'closed': 1, 'approval_denied': 2, 'awaiting_approval': 3, 'in_progress': 4, 'open': 5 };
        aValue = statusOrder[aValue.toLowerCase().replace(/ /g, '_') as keyof typeof statusOrder] || 99;
        bValue = statusOrder[bValue.toLowerCase().replace(/ /g, '_') as keyof typeof statusOrder] || 99;
      }
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [tickets, sortConfig]);

  const handleSort = (column: keyof Ticket) => {
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

  const chartData = useMemo(() => {
    if (!tickets || !tickets.length) return { severity: [], status: [], monthly: [] };

    // Severity counts
    const severityCount: { [key: string]: number } = {};
    tickets.forEach(ticket => {
      severityCount[ticket.severity] = (severityCount[ticket.severity] || 0) + 1;
    });
    const severityOrder = { 'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4 };
    const severity = Object.entries(severityCount).map(([name, value]) => ({ name: formatter(name), value })).sort((a, b) => (severityOrder[b.name as keyof typeof severityOrder] || 99) - (severityOrder[a.name as keyof typeof severityOrder] || 99));

    // Status counts
    const statusCount: { [key: string]: number } = {};
    tickets.forEach(ticket => {
      statusCount[ticket.status] = (statusCount[ticket.status] || 0) + 1;
    });
    const statusOrder = { 'Open': 1, 'In Progress': 2, 'Awaiting Approval': 3, 'Approval Denied': 4, 'Closed': 5 };
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
          <li className="mb-2"><a href="#" className="hover:text-gray-300">Tickets</a></li>
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
                <Legend content={(props) => <CustomLegend {...props} order={['Open', 'In Progress', 'Awaiting Approval', 'Approval Denied', 'Closed']} />} layout="vertical" verticalAlign="middle" align="right" iconType="circle" wrapperStyle={{ transform: 'translateX(-5px)' }} />
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
          <h2 className="text-xl font-semibold p-4 bg-gray-100">All Tickets</h2>
          <div className="overflow-x-auto max-h-128 overflow-y-auto">
            <table className="w-full table-auto">
              <thead className="bg-gray-200 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">ID</th>
                  <th className="px-4 py-2 text-left">Title</th>
                  <th className="px-4 py-2 text-left">Description</th>
                  <th className="px-4 py-2 text-left cursor-pointer" onClick={() => handleSort('category')}>Category <span style={{ color: sortConfig.column === 'category' ? 'red' : 'grey', fontWeight: sortConfig.column === 'category' ? 'bolder' : 'normal' }}>{sortConfig.column === 'category' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer" onClick={() => handleSort('severity')}>Severity <span style={{ color: sortConfig.column === 'severity' ? 'red' : 'grey', fontWeight: sortConfig.column === 'severity' ? 'bolder' : 'normal' }}>{sortConfig.column === 'severity' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer" onClick={() => handleSort('status')}>Status <span style={{ color: sortConfig.column === 'status' ? 'red' : 'grey', fontWeight: sortConfig.column === 'status' ? 'bolder' : 'normal' }}>{sortConfig.column === 'status' ? (sortConfig.direction === 'desc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer" onClick={() => handleSort('assigned_to')}>Assigned To <span style={{ color: sortConfig.column === 'assigned_to' ? 'red' : 'grey', fontWeight: sortConfig.column === 'assigned_to' ? 'bolder' : 'normal' }}>{sortConfig.column === 'assigned_to' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left cursor-pointer" onClick={() => handleSort('date_created')}>Date Created <span style={{ color: sortConfig.column === 'date_created' ? 'red' : 'grey', fontWeight: sortConfig.column === 'date_created' ? 'bolder' : 'normal' }}>{sortConfig.column === 'date_created' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↓'}</span></th>
                  <th className="px-4 py-2 text-left">Attachments</th>
                </tr>
              </thead>
              <tbody>
                {sortedTickets.map((ticket) => (
                  <tr key={ticket.id} className="border-t">
                    <td className="px-4 py-2">{ticket.id}</td>
                    <td className="px-4 py-2">{ticket.title}</td>
                    <td className="px-4 py-2">{ticket.description}</td>
                    <td className="px-4 py-2">{ticket.category}</td>
                    <td className="px-4 py-2" style={{ color: getSeverityColor(ticket.severity) }}>{formatter(ticket.severity)}</td>
                    <td className="px-4 py-2" style={{ color: getStatusColor(ticket.status) }}>{formatter(ticket.status)}</td>
                    <td className="px-4 py-2">{ticket.assigned_to}</td>
                    <td className="px-4 py-2">{(() => {
                      const date = new Date(ticket.date_created);
                      return `${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}/${(date.getFullYear() % 100).toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
                    })()}</td>
                    <td className="px-4 py-2">{ticket.attachment_upload || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

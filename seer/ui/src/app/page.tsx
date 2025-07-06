'use client';

import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';

export default function DashboardPage() {
  const [selectedSection, setSelectedSection] = React.useState<string | null>(null);

  const handleSectionClick = (section: string) => {
    setSelectedSection(section);
  };

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-gray-900 via-gray-800 to-gray-700 font-sans">
      {/* Sidebar */}
      <aside className="w-60 bg-gradient-to-b from-gray-950 to-gray-800 shadow-xl flex flex-col p-6 rounded-tr-3xl rounded-br-3xl border-r border-gray-700">
        <div className="text-3xl font-extrabold text-white tracking-tight mb-10 flex items-center gap-2">
          <span className="inline-block w-3 h-3 bg-blue-500 rounded-full mr-2"></span>
          Seer Copilot
        </div>
        <nav className="flex flex-col gap-4 text-lg">
          <a href="#" className="text-gray-200 hover:text-blue-400 font-semibold transition">Dashboard</a>
          <a href="#" className="text-gray-400 hover:text-blue-400 transition">Rules</a>
          <a href="#" className="text-gray-400 hover:text-blue-400 transition">Trades</a>
          <a href="#" className="text-gray-400 hover:text-blue-400 transition">Replay</a>
        </nav>
        <div className="mt-auto text-xs text-gray-500 pt-10">v0.1 MVP</div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-20 bg-gradient-to-r from-gray-950 to-gray-800 shadow flex items-center px-12 justify-between rounded-bl-3xl border-b border-gray-700">
          <div className="text-2xl font-bold text-white tracking-tight">Dashboard</div>
          <Dialog.Root>
            <Dialog.Trigger asChild>
              <button className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 transition">Open Dialog</button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
              <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white p-8 rounded-2xl shadow-2xl z-50 w-96">
                <Dialog.Title className="text-xl font-bold mb-2">Radix UI Dialog</Dialog.Title>
                <Dialog.Description className="mb-4 text-gray-500">This is a placeholder dialog using Radix UI.</Dialog.Description>
                <Dialog.Close asChild>
                  <button className="mt-2 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">Close</button>
                </Dialog.Close>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </header>

        {/* Dashboard Content */}
        <main className="flex-1 p-10 grid grid-cols-1 md:grid-cols-3 gap-10">
          {/* Live Price Widget */}
          <section 
            className="bg-gradient-to-br from-blue-900 to-blue-700 rounded-2xl shadow-xl p-8 flex flex-col items-center justify-center border border-blue-800 cursor-pointer transform transition-all duration-200 hover:scale-105 hover:shadow-2xl hover:border-blue-600"
            onClick={() => handleSectionClick('live-price')}
          >
            <div className="text-gray-200 text-base mb-2">Live Price</div>
            <div className="text-4xl font-extrabold text-white drop-shadow">$4,505.23</div>
            <div className="text-xs text-blue-200 mt-1">(Simulated)</div>
            <div className="text-xs text-blue-300 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">Click to view details</div>
          </section>

          {/* Rules Table Placeholder */}
          <section 
            className="bg-gradient-to-br from-gray-800 to-gray-700 rounded-2xl shadow-xl p-8 col-span-2 border border-gray-700 cursor-pointer transform transition-all duration-200 hover:scale-[1.02] hover:shadow-2xl hover:border-gray-600"
            onClick={() => handleSectionClick('rules')}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="text-gray-300 text-base font-semibold">Active Rules</div>
              <div className="text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">Click to manage rules</div>
            </div>
            <table className="w-full text-left">
              <thead>
                <tr className="text-xs text-gray-400">
                  <th className="py-1">Name</th>
                  <th className="py-1">Expression</th>
                  <th className="py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="hover:bg-gray-900/40 transition">
                  <td className="py-2 font-medium text-white">High price ping</td>
                  <td className="py-2 text-blue-200">value &gt;= 105</td>
                  <td className="py-2 text-green-400 font-semibold">Active</td>
                </tr>
                <tr className="hover:bg-gray-900/40 transition">
                  <td className="py-2 font-medium text-white">Low price alert</td>
                  <td className="py-2 text-blue-200">value &lt;= 95</td>
                  <td className="py-2 text-green-400 font-semibold">Active</td>
                </tr>
                <tr className="hover:bg-gray-900/40 transition">
                  <td className="py-2 font-medium text-white">Tick milestone</td>
                  <td className="py-2 text-blue-200">tick % 10 == 0</td>
                  <td className="py-2 text-green-400 font-semibold">Active</td>
                </tr>
              </tbody>
            </table>
          </section>

          {/* Trades Table Placeholder */}
          <section 
            className="bg-gradient-to-br from-gray-800 to-gray-700 rounded-2xl shadow-xl p-8 col-span-3 border border-gray-700 cursor-pointer transform transition-all duration-200 hover:scale-[1.01] hover:shadow-2xl hover:border-gray-600"
            onClick={() => handleSectionClick('trades')}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="text-gray-300 text-base font-semibold">Recent Trades</div>
              <div className="text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">Click to view full trade history</div>
            </div>
            <table className="w-full text-left">
              <thead>
                <tr className="text-xs text-gray-400">
                  <th className="py-1">Time</th>
                  <th className="py-1">Side</th>
                  <th className="py-1">Qty</th>
                  <th className="py-1">Entry</th>
                  <th className="py-1">Exit</th>
                  <th className="py-1">P&L</th>
                  <th className="py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="hover:bg-gray-900/40 transition">
                  <td className="py-2 text-white">2025-07-06 10:30</td>
                  <td className="py-2 text-blue-400 font-semibold">Buy</td>
                  <td className="py-2 text-white">100</td>
                  <td className="py-2 text-white">450.50</td>
                  <td className="py-2 text-white">451.25</td>
                  <td className="py-2 text-green-400 font-semibold">+75.00</td>
                  <td className="py-2 text-green-400 font-semibold">Closed</td>
                </tr>
                <tr className="hover:bg-gray-900/40 transition">
                  <td className="py-2 text-white">2025-07-06 10:15</td>
                  <td className="py-2 text-red-400 font-semibold">Sell</td>
                  <td className="py-2 text-white">50</td>
                  <td className="py-2 text-white">452.00</td>
                  <td className="py-2 text-white">451.00</td>
                  <td className="py-2 text-red-400 font-semibold">-50.00</td>
                  <td className="py-2 text-green-400 font-semibold">Closed</td>
                </tr>
              </tbody>
            </table>
          </section>
        </main>
      </div>

      {/* Section Detail Modal */}
      <Dialog.Root open={!!selectedSection} onOpenChange={() => setSelectedSection(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60 z-40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-gray-800 p-8 rounded-2xl shadow-2xl z-50 w-[600px] max-h-[80vh] overflow-y-auto border border-gray-700">
            <Dialog.Title className="text-2xl font-bold text-white mb-4">
              {selectedSection === 'live-price' && 'Live Price Details'}
              {selectedSection === 'rules' && 'Rules Management'}
              {selectedSection === 'trades' && 'Trade History'}
            </Dialog.Title>
            <Dialog.Description className="mb-6 text-gray-300">
              {selectedSection === 'live-price' && 'Detailed view of current market prices and indicators.'}
              {selectedSection === 'rules' && 'Manage your trading rules and conditions.'}
              {selectedSection === 'trades' && 'Complete history of all trades and performance metrics.'}
            </Dialog.Description>
            
            <div className="text-gray-300">
              {selectedSection === 'live-price' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-700 p-4 rounded-lg">
                      <div className="text-sm text-gray-400">Current Price</div>
                      <div className="text-2xl font-bold text-white">$4,505.23</div>
                    </div>
                    <div className="bg-gray-700 p-4 rounded-lg">
                      <div className="text-sm text-gray-400">24h Change</div>
                      <div className="text-2xl font-bold text-green-400">+1.2%</div>
                    </div>
                  </div>
                  <div className="bg-gray-700 p-4 rounded-lg">
                    <div className="text-sm text-gray-400 mb-2">Technical Indicators</div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div>RSI: 65.4</div>
                      <div>MACD: Bullish</div>
                      <div>ATR: 12.3</div>
                    </div>
                  </div>
                </div>
              )}
              
              {selectedSection === 'rules' && (
                <div className="space-y-4">
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition">
                    + Add New Rule
                  </button>
                  <div className="space-y-2">
                    <div className="bg-gray-700 p-4 rounded-lg flex justify-between items-center">
                      <div>
                        <div className="font-medium text-white">High price ping</div>
                        <div className="text-sm text-gray-400">value &gt;= 105</div>
                      </div>
                      <div className="flex gap-2">
                        <button className="bg-gray-600 px-3 py-1 rounded text-sm hover:bg-gray-500">Edit</button>
                        <button className="bg-red-600 px-3 py-1 rounded text-sm hover:bg-red-500">Delete</button>
                      </div>
                    </div>
                    <div className="bg-gray-700 p-4 rounded-lg flex justify-between items-center">
                      <div>
                        <div className="font-medium text-white">Low price alert</div>
                        <div className="text-sm text-gray-400">value &lt;= 95</div>
                      </div>
                      <div className="flex gap-2">
                        <button className="bg-gray-600 px-3 py-1 rounded text-sm hover:bg-gray-500">Edit</button>
                        <button className="bg-red-600 px-3 py-1 rounded text-sm hover:bg-red-500">Delete</button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {selectedSection === 'trades' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="bg-gray-700 p-4 rounded-lg">
                      <div className="text-sm text-gray-400">Total Trades</div>
                      <div className="text-2xl font-bold text-white">24</div>
                    </div>
                    <div className="bg-gray-700 p-4 rounded-lg">
                      <div className="text-sm text-gray-400">Win Rate</div>
                      <div className="text-2xl font-bold text-green-400">68%</div>
                    </div>
                    <div className="bg-gray-700 p-4 rounded-lg">
                      <div className="text-sm text-gray-400">Total P&L</div>
                      <div className="text-2xl font-bold text-green-400">+$1,245</div>
                    </div>
                  </div>
                  <div className="bg-gray-700 p-4 rounded-lg">
                    <div className="text-sm text-gray-400 mb-2">Performance Chart</div>
                    <div className="h-32 bg-gray-600 rounded flex items-center justify-center text-gray-400">
                      Chart placeholder
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <Dialog.Close asChild>
              <button className="mt-6 px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition">
                Close
              </button>
            </Dialog.Close>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

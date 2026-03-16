import { BrowserRouter, Routes, Route, Link } from 'react-router'
import { ImportFlow } from './components/ImportFlow'
import { TransactionList } from './components/TransactionList'

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold text-gray-900 hover:text-indigo-600 transition-colors">
          Cash Canvas
        </Link>
        <Link
          to="/import"
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg font-medium hover:bg-indigo-700 transition-colors"
        >
          Import CSV
        </Link>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  )
}

function HomePage() {
  return (
    <Layout>
      <TransactionList />
    </Layout>
  )
}

function ImportPage() {
  return (
    <Layout>
      <ImportFlow />
    </Layout>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/import" element={<ImportPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

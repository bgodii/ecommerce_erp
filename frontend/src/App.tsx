import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Ads from './pages/Ads'
import BalancoDiario from './pages/BalancoDiario'
import Configuracoes from './pages/Configuracoes'
import Dashboard from './pages/Dashboard'
import Ecommerces from './pages/Ecommerces'
import Entradas from './pages/Entradas'
import EstoqueDiario from './pages/EstoqueDiario'
import Kits from './pages/Kits'
import Login from './pages/Login'
import Precificacao from './pages/Precificacao'
import Produtos from './pages/Produtos'
import Register from './pages/Register'
import Usuarios from './pages/Usuarios'
import Vendas from './pages/Vendas'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/produtos" element={<Produtos />} />
          <Route path="/entradas" element={<Entradas />} />
          <Route path="/vendas" element={<Vendas />} />
          <Route path="/kits" element={<Kits />} />
          <Route path="/ecommerces" element={<Ecommerces />} />
          <Route path="/ads" element={<Ads />} />
          <Route path="/balanco-diario" element={<BalancoDiario />} />
          <Route path="/estoque-diario" element={<EstoqueDiario />} />
          <Route path="/precificacao" element={<Precificacao />} />
          <Route path="/usuarios" element={<Usuarios />} />
          <Route path="/configuracoes" element={<Configuracoes />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

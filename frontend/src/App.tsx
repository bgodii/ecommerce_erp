import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Ads from './pages/Ads'
import AnaliseAds from './pages/AnaliseAds'
import BalancoDiario from './pages/BalancoDiario'
import Ecommerces from './pages/Ecommerces'
import Entradas from './pages/Entradas'
import EstoqueDiario from './pages/EstoqueDiario'
import Home from './pages/Home'
import Imports from './pages/Imports'
import Kits from './pages/Kits'
import Login from './pages/Login'
import Precificacao from './pages/Precificacao'
import Produtos from './pages/Produtos'
import Register from './pages/Register'
import Roas from './pages/Roas'
import Usuarios from './pages/Usuarios'
import Vendas from './pages/Vendas'
import VinculoSkus from './pages/VinculoSkus'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/analise-ads" element={<AnaliseAds />} />
          <Route path="/produtos" element={<Produtos />} />
          <Route path="/entradas" element={<Entradas />} />
          <Route path="/vendas" element={<Vendas />} />
          <Route path="/importar" element={<Imports />} />
          <Route path="/vinculo-skus" element={<VinculoSkus />} />
          <Route path="/kits" element={<Kits />} />
          <Route path="/ecommerces" element={<Ecommerces />} />
          <Route path="/ads" element={<Ads />} />
          <Route path="/balanco-diario" element={<BalancoDiario />} />
          <Route path="/estoque-diario" element={<EstoqueDiario />} />
          <Route path="/precificacao" element={<Precificacao />} />
          <Route path="/roas" element={<Roas />} />
          <Route path="/usuarios" element={<Usuarios />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

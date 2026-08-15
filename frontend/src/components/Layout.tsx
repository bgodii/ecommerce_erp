import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'

const links = [
  { to: '/', label: 'Visão Geral', icon: '📊', end: true },
  { sep: 'Vendas' },
  { to: '/importar', label: 'Importar dados', icon: '📥' },
  { to: '/vinculo-skus', label: 'Vincular SKUs', icon: '🔗' },
  { to: '/vendas', label: 'Vendas', icon: '🛒' },
  { to: '/ads', label: 'Ads (manual)', icon: '📣' },
  { sep: 'Relatórios' },
  { to: '/analise-ads', label: 'Análise de ADS', icon: '📣' },
  { to: '/vinculo-anuncios', label: 'Vincular anúncios', icon: '🔌' },
  { to: '/balanco-diario', label: 'Balanço Diário', icon: '📅' },
  { to: '/estoque-diario', label: 'Estoque Diário', icon: '📉' },
  { to: '/precificacao', label: 'Precificação', icon: '🏷️' },
  { to: '/roas', label: 'Calculadora ROAS', icon: '📈' },
  { sep: 'Cadastros' },
  { to: '/produtos', label: 'Produtos', icon: '👕' },
  { to: '/entradas', label: 'Entradas', icon: '📦' },
  { to: '/kits', label: 'Kits', icon: '🧩' },
  { to: '/ecommerces', label: 'E-commerces', icon: '🏬' },
  { sep: 'Sistema' },
  { to: '/usuarios', label: 'Usuários', icon: '👥' },
]

function initials(name?: string) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?'
}

export default function Layout() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const close = () => setMenuOpen(false)

  return (
    <div className="app">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">🛍️</span>
          <span>eLucroCerto</span>
        </div>
        <nav className="nav">
          {links.map((l, i) =>
            'sep' in l ? (
              <div className="sep" key={i}>
                {l.sep}
              </div>
            ) : (
              <NavLink key={l.to} to={l.to!} end={(l as any).end} onClick={close}>
                <span className="ico" aria-hidden>
                  {l.icon}
                </span>
                <span className="label">{l.label}</span>
              </NavLink>
            ),
          )}
        </nav>
      </aside>
      {menuOpen && <div className="sidebar-backdrop" onClick={close} />}

      <div className="main">
        <div className="topbar">
          <button className="hamburger" onClick={() => setMenuOpen((o) => !o)} aria-label="Menu">
            ☰
          </button>
          <div className="user">
            <div className="who" style={{ textAlign: 'right' }}>
              <b>{user?.name}</b>
              <span>{user?.email}</span>
            </div>
            <div className="avatar">{initials(user?.name)}</div>
            <button className="btn secondary sm" onClick={logout}>
              Sair
            </button>
          </div>
        </div>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  )
}

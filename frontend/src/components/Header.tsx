import uniperLogo from '../assets/uniper-logo.png'

// Uniper-branded application header
export function Header() {
  return (
    <header className="app-header" role="banner">
      <div className="app-header__inner">
        {/* Logo */}
        <div className="app-header__logo">
          <img
            src={uniperLogo}
            alt="Uniper"
            className="app-header__logo-img"
            height={36}
          />
          <div className="app-header__logo-text">
            <span className="app-header__logo-subtitle">Scenario Delta Report</span>
          </div>
        </div>

        {/* Right-side metadata */}
        <div className="app-header__meta">
          <span>UK · EG</span>
        </div>
      </div>
    </header>
  )
}

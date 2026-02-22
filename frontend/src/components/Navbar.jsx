import { NavLink } from 'react-router-dom'

function Navbar() {
    const links = [
        { to: '/', label: 'Dashboard', icon: '📊' },
        { to: '/ask', label: 'Ask & Search', icon: '🤖' },
        { to: '/upload', label: 'Upload', icon: '📤' },
    ]

    return (
        <nav className="sticky top-0 z-50 glass-card border-t-0 rounded-t-none border-x-0">
            <div className="max-w-7xl mx-auto px-4 sm:px-6">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <NavLink to="/" className="flex items-center gap-3 group">
                        <div className="w-9 h-9 bg-gradient-to-br from-brand-500 to-purple-500 rounded-lg flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:shadow-brand-500/40 transition-shadow">
                            <span className="text-white font-bold text-sm">FR</span>
                        </div>
                        <span className="text-lg font-bold gradient-text hidden sm:block">FinRAG</span>
                    </NavLink>

                    {/* Nav Links */}
                    <div className="flex items-center gap-1">
                        {links.map(({ to, label, icon }) => (
                            <NavLink
                                key={to}
                                to={to}
                                className={({ isActive }) =>
                                    `flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${isActive
                                        ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30'
                                        : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                                    }`
                                }
                            >
                                <span>{icon}</span>
                                <span className="hidden sm:inline">{label}</span>
                            </NavLink>
                        ))}
                    </div>
                </div>
            </div>
        </nav>
    )
}

export default Navbar

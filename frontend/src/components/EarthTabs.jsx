import { earthAnalysisTabs } from '../data/placeholderData'

export default function EarthTabs({ activeTab, onTabChange }) {
  return (
    <div className="flex flex-wrap gap-2 p-1 rounded-xl bg-white/5 border border-white/10">
      {earthAnalysisTabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-2.5 rounded-lg font-medium transition-all duration-300 flex items-center gap-2 ${
            activeTab === tab.id
              ? 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/40 shadow-glow'
              : 'text-slate-400 hover:text-accent-cyan hover:bg-white/5 border border-transparent'
          }`}
        >
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </div>
  )
}

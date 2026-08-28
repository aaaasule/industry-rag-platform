import { cn } from './cn';

type TabItem = {
  id: string;
  label: string;
};

type Props = {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
};

export function Tabs({ tabs, active, onChange, className }: Props) {
  return (
    <div className={cn('flex flex-wrap gap-1 border-b border-slate-200', className)}>
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={cn(
              '-mb-px border-b-2 px-3 py-2.5 text-sm transition-colors duration-150',
              isActive
                ? 'border-indigo-600 font-medium text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

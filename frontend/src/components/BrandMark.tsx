type Props = {
  className?: string;
  /** 图标尺寸，默认 28 */
  size?: number;
};

/** 品牌标：几何块面 */
export function BrandMark({ className = '', size = 28 }: Props) {
  const icon = Math.round(size * 0.5);
  return (
    <span
      aria-hidden
      className={[
        'inline-flex shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm',
        className,
      ].join(' ')}
      style={{ width: size, height: size }}
    >
      <svg width={icon} height={icon} viewBox="0 0 14 14" fill="none">
        <path
          d="M2 3.5h4.5V11H3.2A1.2 1.2 0 0 1 2 9.8V3.5ZM7.5 3.5H12V8.8A1.2 1.2 0 0 1 10.8 10H7.5V3.5Z"
          fill="currentColor"
        />
      </svg>
    </span>
  );
}

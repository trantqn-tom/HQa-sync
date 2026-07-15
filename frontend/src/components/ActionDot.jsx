export default function ActionDot({ action }) {
  const cls = action === 'INSERT' ? 'dot green' : action === 'UPDATE' ? 'dot blue' : 'dot gray'
  const label = action === 'INSERT' ? 'Thêm mới' : action === 'UPDATE' ? 'Đã cập nhật' : 'Không thay đổi'
  return <span className="action-badge"><span className={cls}/>{label}</span>
}

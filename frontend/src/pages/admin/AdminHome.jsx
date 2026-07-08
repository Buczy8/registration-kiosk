import AdminLayout from "./AdminLayout.jsx";

export default function AdminHome() {
  return (
    <AdminLayout
      title="Panel administracyjny"
      subtitle="Wybierz sekcję"
      activeHref="/admin"
    />
  );
}

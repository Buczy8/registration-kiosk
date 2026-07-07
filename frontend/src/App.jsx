import { BrowserRouter } from "react-router-dom";
import AppRouter from "./routes/AppRouter.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}

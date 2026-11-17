import "./globals.css";
export const metadata = { title: "Prompt Bank", description: "Validate prompts recursively, keep your instructions enforced." };
export default function Root({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body>{children}</body></html>);
}

import Container from "@/components/ui/Container";
import Section from "@/components/ui/Section";
import { getLanguage, getTranslations } from "@/lib/translations";

export const metadata = {
  title: "Cookies — KOMPLYINT",
  description: "Cookie policy for KOMPLYINT OY website. Information about cookie usage.",
};

export default function CookiesPage({ searchParams }) {
  const lang = getLanguage(searchParams);
  const t = getTranslations(lang);

  return (
    <Section>
      <Container>
        <div className="mx-auto max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            {t.cookies.title}
          </h1>
          <div className="mt-8 space-y-4 text-slate-700">
            {t.cookies.content.map((paragraph, index) => (
              <p key={index} className="leading-relaxed">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </Container>
    </Section>
  );
}

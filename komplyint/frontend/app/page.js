import Container from "@/components/ui/Container";
import Section from "@/components/ui/Section";
import Card from "@/components/ui/Card";
import { getLanguage, getTranslations } from "@/lib/translations";

export const metadata = {
  title: "KOMPLYINT — Compliance readiness",
  description: "Compliance readiness, made practical. We help organisations prepare for regulatory and compliance requirements — clearly, systematically, and without noise.",
};

export default function Home({ searchParams }) {
  const lang = getLanguage(searchParams);
  const t = getTranslations(lang);

  return (
    <>
      {/* 1. HERO SECTION (GREEN) */}
      <Section className="bg-green-50">
        <Container>
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-4xl font-semibold tracking-tight text-slate-900 md:text-5xl">
              {t.home.hero.title}
            </h1>
            <p className="mt-6 text-lg text-slate-700 md:text-xl">
              {t.home.hero.subtitle}
            </p>
            <p className="mt-4 text-sm text-slate-500">
              {t.home.hero.disclaimer}
            </p>
          </div>
        </Container>
      </Section>

      {/* 2. WHAT WE DO (BLUE) */}
      <Section className="bg-blue-50">
        <Container>
          <div className="grid gap-6 md:grid-cols-3">
            <Card variant="green">
              <h2 className="text-xl font-semibold text-slate-900">
                {t.home.whatWeDo.card1.title}
              </h2>
              <p className="mt-3 text-slate-700">
                {t.home.whatWeDo.card1.text}
              </p>
            </Card>
            <Card variant="blue">
              <h2 className="text-xl font-semibold text-slate-900">
                {t.home.whatWeDo.card2.title}
              </h2>
              <p className="mt-3 text-slate-700">
                {t.home.whatWeDo.card2.text}
              </p>
            </Card>
            <Card variant="green">
              <h2 className="text-xl font-semibold text-slate-900">
                {t.home.whatWeDo.card3.title}
              </h2>
              <p className="mt-3 text-slate-700">
                {t.home.whatWeDo.card3.text}
              </p>
            </Card>
          </div>
        </Container>
      </Section>

      {/* 3. WHO WE ARE (GREEN) */}
      <Section className="bg-green-50">
        <Container>
          <div className="mx-auto max-w-3xl">
            <p className="text-lg text-slate-700 leading-relaxed">
              {t.home.whoWeAre.text}
            </p>
          </div>
        </Container>
      </Section>

      {/* 4. HOW WE WORK (BLUE) */}
      <Section className="bg-blue-50">
        <Container>
          <div className="mx-auto max-w-2xl space-y-8">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                {t.home.howWeWork.step1.title}
              </h2>
              <p className="mt-2 text-slate-700">
                {t.home.howWeWork.step1.text}
              </p>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                {t.home.howWeWork.step2.title}
              </h2>
              <p className="mt-2 text-slate-700">
                {t.home.howWeWork.step2.text}
              </p>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                {t.home.howWeWork.step3.title}
              </h2>
              <p className="mt-2 text-slate-700">
                {t.home.howWeWork.step3.text}
              </p>
            </div>
          </div>
        </Container>
      </Section>

      {/* 5. CONTACT CTA (GREEN) */}
      <Section className="bg-green-50">
        <Container>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900">
              {t.home.contact.title}
            </h2>
            <p className="mt-4 text-lg text-slate-700">
              {t.home.contact.text}
            </p>
            <p className="mt-6">
              <a
                href="mailto:komplyint@komplying.com"
                className="text-lg font-medium text-blue-600 hover:text-blue-700 underline"
              >
                komplyint@komplying.com
              </a>
            </p>
          </div>
        </Container>
      </Section>
    </>
  );
}

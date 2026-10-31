import { HourglassIcon } from 'lucide-react'
import PageHeader from '@/components/PageHeader'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'

export default function PlaceholderPage({ title, bolt }: { title: string; bolt: string }) {
  return (
    <section>
      <PageHeader title={title} />
      <Empty className="rounded-xl border border-dashed">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <HourglassIcon />
          </EmptyMedia>
          <EmptyTitle>Coming with {bolt}</EmptyTitle>
          <EmptyDescription>This screen is wired once its backend endpoints land on main.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    </section>
  )
}

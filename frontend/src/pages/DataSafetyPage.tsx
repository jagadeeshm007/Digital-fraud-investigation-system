import PageHeader from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardDescription, CardHeader, CardPanel, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useRole } from '@/lib/role'

// Synthetic examples of the HMAC token format produced by app/masking.py ("***-" + 6 hex chars).
const EXAMPLES = [
  { field: 'Name', raw: 'Priya Nair', masked: '***-4f1a9c' },
  { field: 'Phone', raw: '9876543210', masked: '***-b20e77' },
  { field: 'Email', raw: 'priya.nair@example.com', masked: '***-0c93d2' },
  { field: 'Identity number', raw: 'ABCPN1234K', masked: '***-e81f40' },
]

const SURFACES = [
  { name: 'Screens', detail: 'Every API response masks PII before it leaves the server.' },
  { name: 'AI review', detail: 'Evidence sent to the model is masked first.' },
  { name: 'MCP tools', detail: 'Tool outputs are masked; reveal is never available over MCP.' },
]

export default function DataSafetyPage() {
  const role = useRole()
  return (
    <section className="space-y-5">
      <PageHeader title="Data Safety" description="How personal data is protected across the system." />

      <Card>
        <CardHeader>
          <CardTitle>What is masked</CardTitle>
          <CardDescription>Synthetic examples. The same value always maps to the same token.</CardDescription>
        </CardHeader>
        <CardPanel>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Field</TableHead>
                <TableHead>Stored value</TableHead>
                <TableHead>What users see</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {EXAMPLES.map((e) => (
                <TableRow key={e.field}>
                  <TableCell>{e.field}</TableCell>
                  <TableCell className="text-muted-foreground">{e.raw}</TableCell>
                  <TableCell className="font-mono">{e.masked}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardPanel>
      </Card>

      <div className="grid gap-3 md:grid-cols-3">
        {SURFACES.map((s) => (
          <Card key={s.name}>
            <CardHeader>
              <CardTitle className="text-base">{s.name}</CardTitle>
              <CardDescription>{s.detail}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Revealing a value</CardTitle>
          <CardDescription>
            Only a Supervisor can reveal a masked field, from a case, and every reveal is written to the audit trail.
            Open a case and use Reveal next to a customer field.
          </CardDescription>
        </CardHeader>
        <CardPanel>
          <Badge variant={role === 'supervisor' ? 'success' : 'outline'}>
            {role === 'supervisor' ? 'Your role can reveal' : 'Your role cannot reveal'}
          </Badge>
        </CardPanel>
      </Card>
    </section>
  )
}

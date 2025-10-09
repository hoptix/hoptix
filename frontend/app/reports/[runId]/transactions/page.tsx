"use client"

import * as React from "react"
import { useParams, useRouter } from "next/navigation"
import { IconArrowLeft } from "@tabler/icons-react"
import { RequireAuth } from "@/components/auth/RequireAuth"

import { TransactionsTable } from "@/components/transactions-table"
import { Button } from "@/components/ui/button"

export default function TransactionsPage() {
  const params = useParams()
  const router = useRouter()
  const runId = params.runId as string

  const handleGoBack = () => {
    router.push(`/reports/${runId}`)
  }

  return (
    <RequireAuth>
      <div className="container mx-auto p-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <Button variant="outline" onClick={handleGoBack}>
            <IconArrowLeft className="h-4 w-4 mr-2" />
            Back to Analytics
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Raw Transactions</h1>
            <p className="text-muted-foreground">
              Detailed transaction data for run {runId}
            </p>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <TransactionsTable runId={runId} pageSize={50} />
    </div>
    </RequireAuth>
  )
}

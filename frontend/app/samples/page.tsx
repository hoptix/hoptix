"use client"

import React, { useCallback, useState } from "react"
import { IconUpload, IconCheck } from "@tabler/icons-react"
import { AppLayout } from "@/components/app-layout"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface UploadedSample {
  id: string
  file: File
  preview?: string
  operator?: string
}

const defaultOperators = [
  "Jamarie Moore",
  "Maliaka",
  "Latasha Williams",
]

export default function SamplesPage() {
  const [samples, setSamples] = useState<UploadedSample[]>([])
  const [isDragOver, setIsDragOver] = useState(false)

  const addFiles = useCallback((files: File[]) => {
    const newFiles: UploadedSample[] = files.map((file) => ({
      id: Math.random().toString(36).slice(2, 10),
      file,
      preview: URL.createObjectURL(file),
    }))
    setSamples((prev) => [...prev, ...newFiles])
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    addFiles(files)
  }, [addFiles])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const files = Array.from(e.dataTransfer.files).filter((f) => f.type.startsWith("audio/"))
    addFiles(files)
  }, [addFiles])

  const setOperator = (id: string, operator: string) => {
    setSamples((prev) => prev.map((s) => (s.id === id ? { ...s, operator } : s)))
  }

  const save = () => {
    // TODO: send to API
    const payload = samples.map(({ id, file, operator }) => ({ id, name: file.name, operator }))
    console.log("Saving samples:", payload)
  }

  return (
    <AppLayout>
      <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
        <div className="max-w-4xl mx-auto w-full">
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Samples</CardTitle>
              <CardDescription>
                Upload audio samples of operators and label each sample with the operator's name for voice recognition.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 ${
                  isDragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50"
                }`}
              >
                <IconUpload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <div className="mb-4">
                  <p className="text-lg font-medium">Drop your audio files here</p>
                  <p className="text-muted-foreground">or click to browse</p>
                </div>
                <Label htmlFor="audio-upload" className="cursor-pointer">
                  <Input
                    id="audio-upload"
                    type="file"
                    multiple
                    accept="audio/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Button variant="outline" className="pointer-events-none">
                    Browse Files
                  </Button>
                </Label>
              </div>

              {samples.length > 0 && (
                <div className="mt-6 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium">Uploaded Samples ({samples.length})</h4>
                    <Button size="sm" onClick={save}>
                      <IconCheck className="mr-2 h-4 w-4" /> Save Labels
                    </Button>
                  </div>
                  {samples.map((s) => (
                    <div key={s.id} className="p-3 border rounded-lg bg-muted/20">
                      <div className="flex items-center gap-3">
                        <audio controls className="h-9">
                          <source src={s.preview} />
                        </audio>
                        <div className="flex-1 truncate">
                          <p className="text-sm font-medium truncate max-w-xs">{s.file.name}</p>
                          <p className="text-xs text-muted-foreground">{(s.file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                        <div className="min-w-64">
                          <Label className="text-xs">Operator</Label>
                          <Select value={s.operator || ""} onValueChange={(v) => setOperator(s.id, v)}>
                            <SelectTrigger className="h-9">
                              <SelectValue placeholder="Select name" />
                            </SelectTrigger>
                            <SelectContent>
                              {defaultOperators.map((op) => (
                                <SelectItem key={op} value={op}>{op}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  )
}



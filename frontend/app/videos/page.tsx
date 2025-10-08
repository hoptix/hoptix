"use client"

import React, { useState, useCallback } from 'react'
import {
  IconUpload,
  IconVideo,
  IconX,
  IconLoader2,
  IconClock,
  IconPlayerPlay,
  IconCheck,
  IconAlertTriangle,
  IconRefresh,
  IconTrash,
  IconEye,
  IconDownload,
  IconDotsVertical,
  IconTag,
  IconChevronLeft,
  IconChevronRight,
  IconBuilding,
  IconCalendar,
  IconUsers
} from '@tabler/icons-react'
import { format } from 'date-fns'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { AppLayout } from '@/components/app-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Calendar } from '@/components/ui/calendar'

interface UploadedFile {
  file: File
  id: string
  preview?: string
  startTime?: string
  endTime?: string
  operatorName?: string
}

interface Restaurant {
  id: string
  name: string
  location: string
  address: string
}

interface OperatorAssignment {
  videoId: string
  operatorName: string
  startTime: string
  endTime: string
}

interface CommissioningStep {
  id: number
  title: string
  description: string
  completed: boolean
}

// Sample restaurants
const sampleRestaurants: Restaurant[] = [
  { id: "mcd_downtown", name: "McDonald's", location: "Downtown Seattle", address: "1234 Pine St, Seattle, WA" },
  { id: "subway_bellevue", name: "Subway", location: "Bellevue Square", address: "575 Bellevue Square, Bellevue, WA" },
  { id: "bk_capitol", name: "Burger King", location: "Capitol Hill", address: "1122 E Pine St, Seattle, WA" },
  { id: "sbux_university", name: "Starbucks", location: "University District", address: "4555 University Way NE, Seattle, WA" },
  { id: "cfa_southcenter", name: "Chick-fil-A", location: "Southcenter Mall", address: "17500 Southcenter Pkwy, Tukwila, WA" },
  { id: "tb_fremont", name: "Taco Bell", location: "Fremont Ave", address: "3213 Fremont Ave N, Seattle, WA" },
  { id: "kfc_ballard", name: "KFC", location: "Ballard", address: "5963 15th Ave NW, Seattle, WA" }
]

// Sample operator names
const sampleOperators = [
  "Sarah Johnson", "Mike Chen", "Lisa Rodriguez", "David Kim", "Emma Davis",
  "Tom Wilson", "Alex Turner", "Carlos Mendez", "Jennifer Lee", "Ryan Park",
  "Maria Garcia", "James Wright", "Anna Kowalski", "Chris Thompson"
]

interface VideoFile {
  id: string
  filename: string
  fileSize: number
  duration: number // in seconds
  startTime: string // time of day like "09:30"
  endTime: string // time of day like "11:30"
  operatorName?: string // to be labeled by user
}

interface ProcessingRun {
  id: string
  runId: string
  restaurantName: string
  restaurantLocation: string
  date: Date
  uploadedAt: Date
  status: 'pending' | 'labeling' | 'processing' | 'completed' | 'error'
  errorCode?: string
  progress?: number
  estimatedTime?: number
  processingStarted?: Date
  processingCompleted?: Date
  processingTime?: string // actual processing time
  cost: string // processing cost
  videoFiles: VideoFile[]
  totalVideos: number
  totalDuration: number // total duration in seconds
  labeledVideos: number // how many videos have operator labels
  needsLabeling: boolean // whether this run needs operator labeling
}

// Sample restaurant runs with various statuses
const sampleRuns: ProcessingRun[] = [
  {
    id: "run_001",
    runId: "MCDonald_Downtown_20240115",
    restaurantName: "McDonald's",
    restaurantLocation: "Downtown Seattle",
    date: new Date(2024, 0, 15),
    uploadedAt: new Date(2024, 0, 15, 9, 30),
    status: "completed",
    progress: 100,
    processingStarted: new Date(2024, 0, 15, 9, 35),
    processingCompleted: new Date(2024, 0, 15, 10, 22),
    processingTime: "2h 47m",
    cost: "$45.50",
    totalVideos: 6,
    totalDuration: 28800, // 8 hours
    labeledVideos: 6,
    needsLabeling: false,
    videoFiles: [
      { id: "v1", filename: "morning_shift_06_10.mp4", fileSize: 450000000, duration: 14400, startTime: "06:00", endTime: "10:00", operatorName: "Sarah Johnson" },
      { id: "v2", filename: "mid_morning_10_12.mp4", fileSize: 280000000, duration: 7200, startTime: "10:00", endTime: "12:00", operatorName: "Mike Chen" },
      { id: "v3", filename: "lunch_rush_12_14.mp4", fileSize: 320000000, duration: 7200, startTime: "12:00", endTime: "14:00", operatorName: "Lisa Rodriguez" }
    ]
  },
  {
    id: "run_002",
    runId: "Subway_Bellevue_20240115",
    restaurantName: "Subway",
    restaurantLocation: "Bellevue Square",
    date: new Date(2024, 0, 15),
    uploadedAt: new Date(2024, 0, 15, 14, 20),
    status: "labeling",
    processingTime: "-",
    cost: "$32.80",
    totalVideos: 4,
    totalDuration: 21600, // 6 hours
    labeledVideos: 2,
    needsLabeling: true,
    videoFiles: [
      { id: "v4", filename: "opening_shift_09_12.mp4", fileSize: 380000000, duration: 10800, startTime: "09:00", endTime: "12:00", operatorName: "David Kim" },
      { id: "v5", filename: "afternoon_shift_12_15.mp4", fileSize: 420000000, duration: 10800, startTime: "12:00", endTime: "15:00" },
      { id: "v6", filename: "evening_prep_15_18.mp4", fileSize: 390000000, duration: 10800, startTime: "15:00", endTime: "18:00" }
    ]
  },
  {
    id: "run_003",
    runId: "BurgerKing_Capitol_20240114",
    restaurantName: "Burger King",
    restaurantLocation: "Capitol Hill",
    date: new Date(2024, 0, 14),
    uploadedAt: new Date(2024, 0, 14, 20, 15),
    status: "processing",
    progress: 78,
    estimatedTime: 420, // 7 minutes remaining
    processingStarted: new Date(2024, 0, 14, 20, 25),
    processingTime: "1h 23m",
    cost: "$38.40",
    totalVideos: 5,
    totalDuration: 25200, // 7 hours
    labeledVideos: 5,
    needsLabeling: false,
    videoFiles: [
      { id: "v7", filename: "breakfast_shift_07_11.mp4", fileSize: 520000000, duration: 14400, startTime: "07:00", endTime: "11:00", operatorName: "Tom Wilson" },
      { id: "v8", filename: "lunch_period_11_15.mp4", fileSize: 480000000, duration: 14400, startTime: "11:00", endTime: "15:00", operatorName: "Emma Davis" }
    ]
  },
  {
    id: "run_004",
    runId: "Starbucks_University_20240113",
    restaurantName: "Starbucks",
    restaurantLocation: "University District",
    date: new Date(2024, 0, 13),
    uploadedAt: new Date(2024, 0, 13, 16, 45),
    status: "error",
    errorCode: "ERR_CORRUPTED_VIDEO",
    processingTime: "-",
    cost: "$24.00",
    totalVideos: 3,
    totalDuration: 18000, // 5 hours
    labeledVideos: 3,
    needsLabeling: false,
    videoFiles: [
      { id: "v9", filename: "morning_rush_06_10.mp4", fileSize: 450000000, duration: 14400, startTime: "06:00", endTime: "10:00", operatorName: "Alex Turner" }
    ]
  },
  {
    id: "run_005",
    runId: "ChickFilA_Southcenter_20240115",
    restaurantName: "Chick-fil-A",
    restaurantLocation: "Southcenter Mall",
    date: new Date(2024, 0, 15),
    uploadedAt: new Date(2024, 0, 15, 11, 30),
    status: "pending",
    processingTime: "-",
    cost: "$52.50",
    totalVideos: 7,
    totalDuration: 32400, // 9 hours
    labeledVideos: 0,
    needsLabeling: true,
    videoFiles: [
      { id: "v10", filename: "opening_shift_07_10.mp4", fileSize: 380000000, duration: 10800, startTime: "07:00", endTime: "10:00" },
      { id: "v11", filename: "busy_lunch_10_13.mp4", fileSize: 420000000, duration: 10800, startTime: "10:00", endTime: "13:00" },
      { id: "v12", filename: "afternoon_13_16.mp4", fileSize: 390000000, duration: 10800, startTime: "13:00", endTime: "16:00" }
    ]
  },
  {
    id: "run_006",
    runId: "Taco_Bell_Fremont_20240114",
    restaurantName: "Taco Bell",
    restaurantLocation: "Fremont Ave",
    date: new Date(2024, 0, 14),
    uploadedAt: new Date(2024, 0, 14, 22, 10),
    status: "labeling",
    processingTime: "-",
    cost: "$27.00",
    totalVideos: 4,
    totalDuration: 21600, // 6 hours
    labeledVideos: 1,
    needsLabeling: true,
    videoFiles: [
      { id: "v13", filename: "dinner_rush_17_20.mp4", fileSize: 450000000, duration: 10800, startTime: "17:00", endTime: "20:00", operatorName: "Carlos Mendez" },
      { id: "v14", filename: "late_evening_20_23.mp4", fileSize: 380000000, duration: 10800, startTime: "20:00", endTime: "23:00" }
    ]
  },
  {
    id: "run_007",
    runId: "KFC_Ballard_20240112",
    restaurantName: "KFC",
    restaurantLocation: "Ballard",
    date: new Date(2024, 0, 12),
    uploadedAt: new Date(2024, 0, 12, 15, 20),
    status: "completed",
    progress: 100,
    processingStarted: new Date(2024, 0, 12, 15, 25),
    processingCompleted: new Date(2024, 0, 12, 16, 18),
    processingTime: "3h 12m",
    cost: "$40.50",
    totalVideos: 5,
    totalDuration: 25200, // 7 hours
    labeledVideos: 5,
    needsLabeling: false,
    videoFiles: [
      { id: "v15", filename: "full_day_coverage.mp4", fileSize: 680000000, duration: 25200, startTime: "11:00", endTime: "18:00", operatorName: "Jennifer Lee" }
    ]
  }
]

export default function VideosPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [processingRuns, setProcessingRuns] = useState<ProcessingRun[]>(sampleRuns)
  const [activeTab, setActiveTab] = useState("commission")
  
  // Error dialog state
  const [selectedErrorRun, setSelectedErrorRun] = useState<ProcessingRun | null>(null)
  const [isErrorDialogOpen, setIsErrorDialogOpen] = useState(false)
  
  // Commissioning flow state
  const [currentStep, setCurrentStep] = useState(0)
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null)
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date())
  const [operatorAssignments, setOperatorAssignments] = useState<OperatorAssignment[]>([])
  
  // Generate dynamic time periods for the whole day (hourly slots)
  const generateTimePeriods = () => {
    const periods = []
    for (let hour = 6; hour < 23; hour++) {
      const startTime = `${hour.toString().padStart(2, '0')}:00`
      const endTime = `${(hour + 1).toString().padStart(2, '0')}:00`
      periods.push(`${startTime}-${endTime}`)
    }
    return periods
  }
  
  const timePeriods = generateTimePeriods()
  
  // Error handling
  const getErrorDetails = (errorCode: string) => {
    const errorMap: Record<string, { title: string; description: string; solution: string }> = {
      'ERR_CORRUPTED_VIDEO': {
        title: 'Corrupted Video File',
        description: 'One or more video files in this run appear to be corrupted and cannot be processed.',
        solution: 'Re-upload the video files in a supported format (MP4, MOV, AVI, WebM) and ensure they are not corrupted.'
      },
      'ERR_INSUFFICIENT_STORAGE': {
        title: 'Insufficient Storage',
        description: 'There is not enough storage space available to process this run.',
        solution: 'Try reducing the number of video files or contact support to increase your storage quota.'
      },
      'ERR_PROCESSING_TIMEOUT': {
        title: 'Processing Timeout',
        description: 'The video processing took too long and timed out.',
        solution: 'Try splitting large video files into smaller segments or contact support for assistance.'
      },
      'ERR_INVALID_FORMAT': {
        title: 'Invalid Video Format',
        description: 'One or more video files are in an unsupported format.',
        solution: 'Convert your videos to a supported format: MP4 (recommended), MOV, AVI, or WebM.'
      },
      'ERR_NETWORK_FAILURE': {
        title: 'Network Connection Error',
        description: 'The processing failed due to a network connectivity issue.',
        solution: 'Check your internet connection and try reprocessing the run.'
      }
    }
    
    return errorMap[errorCode] || {
      title: 'Unknown Error',
      description: 'An unexpected error occurred during processing.',
      solution: 'Please contact support for assistance with this issue.'
    }
  }
  
  const handleErrorRowClick = (run: ProcessingRun) => {
    if (run.status === 'error') {
      setSelectedErrorRun(run)
      setIsErrorDialogOpen(true)
    }
  }
  
  const commissioningSteps: CommissioningStep[] = [
    { id: 0, title: "Upload Videos", description: "Upload video files for analysis", completed: uploadedFiles.length > 0 },
    { id: 1, title: "Select Restaurant", description: "Choose the restaurant location", completed: selectedRestaurant !== null },
    { id: 2, title: "Select Date", description: "Choose the date for this run", completed: selectedDate !== undefined },
    { id: 3, title: "Assign Operators", description: "Assign operators to time periods", completed: operatorAssignments.some(a => a.operatorName) },
    { id: 4, title: "Review & Submit", description: "Review details and create run", completed: false }
  ]





  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    } else {
      return `${secs}s`
    }
  }

  const getStatusIcon = (status: ProcessingRun['status']) => {
    switch (status) {
      case 'pending':
        return <IconClock className="h-4 w-4" />
      case 'labeling':
        return <IconVideo className="h-4 w-4" />
      case 'processing':
        return <IconPlayerPlay className="h-4 w-4" />
      case 'completed':
        return <IconCheck className="h-4 w-4" />
      case 'error':
        return <IconAlertTriangle className="h-4 w-4" />
      default:
        return <IconClock className="h-4 w-4" />
    }
  }

  const getStatusBadge = (run: ProcessingRun) => {
    switch (run.status) {
      case 'pending':
        return <Badge variant="secondary" className="bg-gray-100 text-gray-700">Pending Upload</Badge>
      case 'labeling':
        return (
          <Badge variant="secondary" className="bg-yellow-100 text-yellow-700">
            Needs Labeling ({run.labeledVideos}/{run.totalVideos})
          </Badge>
        )
      case 'processing':
        return (
          <Badge variant="secondary" className="bg-blue-100 text-blue-700">
            Processing ({run.progress}%)
          </Badge>
        )
      case 'completed':
        return <Badge variant="secondary" className="bg-green-100 text-green-700">Completed</Badge>
      case 'error':
        return (
          <Badge variant="secondary" className="bg-red-100 text-red-700">
            Error: {run.errorCode}
          </Badge>
        )
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  const retryRun = (runId: string) => {
    setProcessingRuns(prev => prev.map(run => 
      run.id === runId 
        ? { ...run, status: 'pending' as const, errorCode: undefined }
        : run
    ))
  }

  const deleteRun = (runId: string) => {
    setProcessingRuns(prev => prev.filter(run => run.id !== runId))
  }

  const startLabeling = (runId: string) => {
    setProcessingRuns(prev => prev.map(run => 
      run.id === runId 
        ? { ...run, status: 'labeling' as const }
        : run
    ))
  }

  const getRunStats = () => {
    const stats = processingRuns.reduce((acc, run) => {
      acc[run.status] = (acc[run.status] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    
    return {
      total: processingRuns.length,
      pending: stats.pending || 0,
      labeling: stats.labeling || 0,
      processing: stats.processing || 0,
      completed: stats.completed || 0,
      error: stats.error || 0
    }
  }

  const runStats = getRunStats()

  const nextStep = () => {
    if (currentStep < commissioningSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const canProceedToNext = () => {
    return commissioningSteps[currentStep].completed
  }

  const canCreateRun = () => {
    // On the final step, check if all previous steps are completed
    if (currentStep === commissioningSteps.length - 1) {
      return commissioningSteps.slice(0, -1).every(step => step.completed)
    }
    // On other steps, use normal validation
    return canProceedToNext()
  }

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    addFiles(files)
  }, [])

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
    
    const files = Array.from(e.dataTransfer.files).filter(file => 
      file.type.startsWith('video/')
    )
    
    addFiles(files)
  }, [])

  const addFiles = useCallback((files: File[]) => {
    const newFiles: UploadedFile[] = files.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      preview: URL.createObjectURL(file)
    }))
    
    setUploadedFiles(prev => [...prev, ...newFiles])
    
    // Initialize operator assignments for new files
    const newAssignments = newFiles.map(file => ({
      videoId: file.id,
      operatorName: "",
      startTime: "",
      endTime: ""
    }))
    setOperatorAssignments(prev => [...prev, ...newAssignments])
  }, [])

  const removeFile = useCallback((id: string) => {
    setUploadedFiles(prev => {
      const file = prev.find(f => f.id === id)
      if (file?.preview) {
        URL.revokeObjectURL(file.preview)
      }
      return prev.filter(f => f.id !== id)
    })
    
    // Remove corresponding operator assignment
    setOperatorAssignments(prev => prev.filter(a => a.videoId !== id))
  }, [])

  const updateOperatorAssignment = (videoId: string, field: keyof OperatorAssignment, value: string) => {
    setOperatorAssignments(prev => prev.map(assignment => 
      assignment.videoId === videoId 
        ? { ...assignment, [field]: value }
        : assignment
    ))
  }

  const updateTimeSlotOperator = (timeSlot: string, operatorName: string) => {
    const finalOperatorName = operatorName === "none" ? undefined : operatorName
    setOperatorAssignments(prev => {
      const existingIndex = prev.findIndex(a => a.startTime + '-' + a.endTime === timeSlot)
      if (existingIndex >= 0) {
        if (finalOperatorName === undefined) {
          // Remove the assignment if "none" is selected
          return prev.filter(assignment => assignment.startTime + '-' + assignment.endTime !== timeSlot)
        }
        return prev.map(assignment => 
          assignment.startTime + '-' + assignment.endTime === timeSlot
            ? { ...assignment, operatorName: finalOperatorName }
            : assignment
        )
      } else if (finalOperatorName !== undefined) {
        const [startTime, endTime] = timeSlot.split('-')
        return [...prev, {
          videoId: timeSlot, // Use timeSlot as ID for time-based assignments
          operatorName: finalOperatorName,
          startTime,
          endTime
        }]
      }
      return prev
    })
  }

  const createRun = async () => {
    if (!selectedRestaurant || !selectedDate) return
    
    setIsLoading(true)
    
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      const newRun: ProcessingRun = {
        id: `run_${Date.now()}`,
        runId: `${selectedRestaurant.name.replace(/\s/g, '')}_${selectedRestaurant.location.replace(/\s/g, '')}_${format(selectedDate, 'yyyyMMdd')}`,
        restaurantName: selectedRestaurant.name,
        restaurantLocation: selectedRestaurant.location,
        date: selectedDate,
        uploadedAt: new Date(),
        status: 'labeling',
        totalVideos: uploadedFiles.length,
        totalDuration: uploadedFiles.reduce((total, file) => total + (file.file.size / 1000000 * 60), 0), // rough estimate
        labeledVideos: operatorAssignments.filter(a => a.operatorName).length,
        needsLabeling: operatorAssignments.some(a => !a.operatorName),
        processingTime: "-",
        cost: `$${(uploadedFiles.length * 5).toFixed(2)}`,
        videoFiles: uploadedFiles.map(file => {
          const assignment = operatorAssignments.find(a => a.videoId === file.id)!
          return {
            id: file.id,
            filename: file.file.name,
            fileSize: file.file.size,
            duration: Math.floor(file.file.size / 1000000 * 60), // rough estimate
            startTime: assignment.startTime,
            endTime: assignment.endTime,
            operatorName: assignment.operatorName
          }
        })
      }
      
      setProcessingRuns(prev => [newRun, ...prev])
      
      // Reset form
      uploadedFiles.forEach(file => {
        if (file.preview) {
          URL.revokeObjectURL(file.preview)
        }
      })
      setUploadedFiles([])
      setCurrentStep(0)
      setSelectedRestaurant(null)
      setSelectedDate(new Date())
      setOperatorAssignments([])
      setActiveTab("queue")
      
    } catch (error) {
      console.error('Error creating run:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <RequireAuth>
      <AppLayout>
      <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
        <div className="max-w-6xl mx-auto w-full">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <div className="flex items-center justify-end mb-6 pt-8">
              <TabsList className="grid w-fit grid-cols-2">
                <TabsTrigger value="commission">Commission Run</TabsTrigger>
                <TabsTrigger value="queue" className="relative">
                  Processing Queue
                  {(runStats.labeling + runStats.processing) > 0 && (
                    <Badge className="ml-2 bg-blue-500 text-white px-1.5 py-0.5 text-xs">
                      {runStats.labeling + runStats.processing}
                    </Badge>
                  )}
                </TabsTrigger>
              </TabsList>
        </div>

            <TabsContent value="commission" className="space-y-6">
              {/* Navigation Controls */}
              <div className="flex justify-between items-center mb-6">
                <Button
                  variant="outline"
                  onClick={prevStep}
                  disabled={currentStep === 0}
                  className="transition-all duration-200"
                >
                  <IconChevronLeft className="mr-2 h-4 w-4" />
                  Previous
                </Button>
                
                <div className="flex gap-2">
                  {commissioningSteps.map((_, index) => (
                    <div
                      key={index}
                      className={`w-2 h-2 rounded-full transition-all duration-300 ${
                        index === currentStep ? 'bg-primary w-6' : index < currentStep ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    />
                  ))}
                </div>
                
                <Button
                  onClick={nextStep}
                  disabled={currentStep === commissioningSteps.length - 1 || !canProceedToNext()}
                  className="transition-all duration-200"
                >
                  Next
                  <IconChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </div>

              {/* Step Content with Smooth Transitions */}
              <div className="relative overflow-hidden">
                <div 
                  className="flex transition-transform duration-500 ease-in-out"
                  style={{ transform: `translateX(-${currentStep * 100}%)` }}
                >
                  {/* Step 0: Upload Videos */}
                  <div className="w-full flex-shrink-0">
                    <Card>
            <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <IconUpload className="h-5 w-5" />
                          Upload Videos
                        </CardTitle>
              <CardDescription>
                          Upload video files for the restaurant run. Supported formats: MP4, MOV, AVI, WebM
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 ${
                  isDragOver 
                              ? 'border-primary bg-primary/5 scale-[1.02]' 
                    : 'border-muted-foreground/25 hover:border-muted-foreground/50'
                }`}
              >
                <IconUpload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <div className="mb-4">
                  <p className="text-lg font-medium">Drop your video files here</p>
                  <p className="text-muted-foreground">or click to browse</p>
                </div>
                <Label htmlFor="video-upload" className="cursor-pointer">
                  <Input
                    id="video-upload"
                    type="file"
                    multiple
                    accept="video/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Button variant="outline" className="pointer-events-none">
                    Browse Files
                  </Button>
                </Label>
              </div>

          {uploadedFiles.length > 0 && (
                          <div className="mt-6 space-y-3 animate-in slide-in-from-top-2 duration-300">
                            <h4 className="font-medium">Uploaded Files ({uploadedFiles.length})</h4>
                            {uploadedFiles.map((file, index) => (
                              <div 
                                key={file.id} 
                                className="flex items-center justify-between p-3 border rounded-lg bg-muted/20 animate-in slide-in-from-left-1 duration-300"
                                style={{ animationDelay: `${index * 100}ms` }}
                              >
                      <div className="flex items-center gap-3">
                                  <IconVideo className="h-6 w-6 text-primary" />
                        <div>
                          <p className="font-medium">{file.file.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatFileSize(file.file.size)} • {file.file.type}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(file.id)}
                                  className="text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <IconX className="h-4 w-4" />
                      </Button>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>

                  {/* Step 1: Select Restaurant */}
                  <div className="w-full flex-shrink-0">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <IconBuilding className="h-5 w-5" />
                          Select Restaurant
                        </CardTitle>
                        <CardDescription>
                          Choose the restaurant location for this video run
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {sampleRestaurants.map((restaurant, index) => (
                            <div
                              key={restaurant.id}
                              onClick={() => setSelectedRestaurant(restaurant)}
                              className={`p-4 border-2 rounded-lg cursor-pointer transition-all duration-200 animate-in fade-in-0 slide-in-from-bottom-2 ${
                                selectedRestaurant?.id === restaurant.id
                                  ? 'border-primary bg-primary/5 shadow-md scale-[1.02]'
                                  : 'border-gray-200 hover:border-gray-300 hover:shadow-sm hover:scale-[1.01]'
                              }`}
                              style={{ animationDelay: `${index * 100}ms` }}
                            >
                              <div className="flex items-start gap-3">
                                <IconBuilding className="h-5 w-5 text-primary mt-0.5" />
                                <div className="flex-1">
                                  <h4 className="font-medium">{restaurant.name}</h4>
                                  <p className="text-sm text-muted-foreground">{restaurant.location}</p>
                                  <p className="text-xs text-muted-foreground mt-1">{restaurant.address}</p>
                                </div>
                                {selectedRestaurant?.id === restaurant.id && (
                                  <IconCheck className="h-5 w-5 text-primary animate-in zoom-in-75 duration-200" />
                                )}
                              </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
                  </div>

                  {/* Step 2: Select Date */}
                  <div className="w-full flex-shrink-0">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <IconCalendar className="h-5 w-5" />
                          Select Date
                        </CardTitle>
                        <CardDescription>
                          Choose the date when these videos were recorded
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-col items-center space-y-4">
                          <div className="animate-in fade-in-0 slide-in-from-top-2 duration-500">
                            <Calendar
                              mode="single"
                              selected={selectedDate}
                              onSelect={setSelectedDate}
                              className="rounded-md border"
                              disabled={(date) => date > new Date() || date < new Date("1900-01-01")}
                            />
                          </div>
                          {selectedDate && (
                            <div className="text-center p-4 bg-muted/20 rounded-lg animate-in zoom-in-95 slide-in-from-bottom-2 duration-300">
                              <p className="font-medium">Selected Date</p>
                              <p className="text-lg text-primary">{format(selectedDate, 'MMMM dd, yyyy')}</p>
                              <p className="text-sm text-muted-foreground">{format(selectedDate, 'EEEE')}</p>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Step 3: Assign Operators */}
                  <div className="w-full flex-shrink-0">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <IconUsers className="h-5 w-5" />
                          Assign Operators
                        </CardTitle>
                        <CardDescription>
                          Assign operators to time periods extracted from video filenames
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="mb-6">
                          <h4 className="font-medium mb-3">Daily Time Periods</h4>
                          <div className="text-sm text-muted-foreground mb-4">
                            Assign operators to hourly time slots throughout the day (6:00 AM - 11:00 PM)
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {timePeriods.map((timePeriod, index) => {
                            const assignment = operatorAssignments.find(a => a.startTime + '-' + a.endTime === timePeriod)
                            const [startTime, endTime] = timePeriod.split('-')
                            
                            return (
                              <div 
                                key={timePeriod} 
                                className="p-4 border rounded-lg bg-gradient-to-br from-blue-50 to-indigo-50 animate-in slide-in-from-left-2 duration-300"
                                style={{ animationDelay: `${index * 50}ms` }}
                              >
                                <div className="flex items-center gap-3 mb-3">
                                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                                    <IconClock className="h-5 w-5 text-blue-600" />
                                  </div>
                                  <div>
                                    <p className="font-semibold">{startTime} - {endTime}</p>
                                    <p className="text-xs text-muted-foreground">1 hour slot</p>
                                  </div>
                                </div>
                                
                                <div>
                                  <Label className="text-sm font-medium">Operator</Label>
                                  <Select 
                                    value={assignment?.operatorName || "none"} 
                                    onValueChange={(value) => updateTimeSlotOperator(timePeriod, value)}
                                  >
                                    <SelectTrigger className="mt-1 transition-all duration-200 hover:scale-[1.01]">
                                      <SelectValue placeholder="Select operator" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="none">No operator</SelectItem>
                                      {sampleOperators.map((operator) => (
                                        <SelectItem key={operator} value={operator}>
                                          {operator}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Step 4: Review & Submit */}
                  <div className="w-full flex-shrink-0">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <IconCheck className="h-5 w-5" />
                          Review & Submit
                        </CardTitle>
                        <CardDescription>
                          Review your run details and submit for processing
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-4 animate-in slide-in-from-left-2 duration-500">
                            <div>
                              <h4 className="font-medium mb-2">Restaurant Details</h4>
                              <div className="p-3 bg-muted/20 rounded-lg">
                                <p className="font-medium">{selectedRestaurant?.name}</p>
                                <p className="text-sm text-muted-foreground">{selectedRestaurant?.location}</p>
                                <p className="text-xs text-muted-foreground">{selectedRestaurant?.address}</p>
                              </div>
                            </div>
                            
                            <div>
                              <h4 className="font-medium mb-2">Run Date</h4>
                              <div className="p-3 bg-muted/20 rounded-lg">
                                <p className="font-medium">{selectedDate && format(selectedDate, 'MMMM dd, yyyy')}</p>
                                <p className="text-sm text-muted-foreground">{selectedDate && format(selectedDate, 'EEEE')}</p>
                              </div>
                            </div>
                          </div>
                          
                          <div className="animate-in slide-in-from-right-2 duration-500">
                            <h4 className="font-medium mb-2">Operator Assignments ({operatorAssignments.filter(a => a.operatorName).length} assigned)</h4>
                            <div className="space-y-3 max-h-64 overflow-y-auto">
                              {operatorAssignments.filter(a => a.operatorName).map((assignment, index) => {
                                return (
                                  <div 
                                    key={assignment.videoId} 
                                    className="p-3 bg-muted/20 rounded text-sm animate-in fade-in-0 slide-in-from-bottom-1 duration-300"
                                    style={{ animationDelay: `${index * 100}ms` }}
                                  >
                                    <div className="flex items-center justify-between mb-1">
                                      <p className="font-medium">{assignment.startTime} - {assignment.endTime}</p>
                                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                        1 hour slot
                                      </span>
                                    </div>
                                    <p className="text-muted-foreground">
                                      Operator: {assignment.operatorName}
                                    </p>
                                  </div>
                                )
                              })}
                              {operatorAssignments.filter(a => a.operatorName).length === 0 && (
                                <div className="text-center py-8 text-muted-foreground">
                                  <p>No operators assigned yet</p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex justify-center animate-in zoom-in-95 duration-500 delay-300">
              <Button 
                            onClick={createRun}
                            disabled={isLoading || !canCreateRun()}
                size="lg"
                            className="min-w-48 transition-all duration-200 hover:scale-105"
              >
                {isLoading ? (
                  <>
                    <IconLoader2 className="mr-2 h-4 w-4 animate-spin" />
                                Creating Run...
                  </>
                ) : (
                  <>
                                <IconCheck className="mr-2 h-4 w-4" />
                                Create Run
                              </>
                            )}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </div>

            </TabsContent>

            <TabsContent value="queue" className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <IconClock className="h-5 w-5 text-gray-500" />
                      <div>
                        <p className="text-2xl font-bold">{runStats.pending}</p>
                        <p className="text-sm text-muted-foreground">Pending</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <IconTag className="h-5 w-5 text-yellow-500" />
                      <div>
                        <p className="text-2xl font-bold">{runStats.labeling}</p>
                        <p className="text-sm text-muted-foreground">Labeling</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <IconPlayerPlay className="h-5 w-5 text-blue-500" />
                      <div>
                        <p className="text-2xl font-bold">{runStats.processing}</p>
                        <p className="text-sm text-muted-foreground">Processing</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <IconCheck className="h-5 w-5 text-green-500" />
                      <div>
                        <p className="text-2xl font-bold">{runStats.completed}</p>
                        <p className="text-sm text-muted-foreground">Completed</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <IconAlertTriangle className="h-5 w-5 text-red-500" />
                      <div>
                        <p className="text-2xl font-bold">{runStats.error}</p>
                        <p className="text-sm text-muted-foreground">Errors</p>
                      </div>
              </div>
            </CardContent>
          </Card>
              </div>

              <Card>
              <CardHeader>
                  <CardTitle>Processing Queue - Restaurant Runs</CardTitle>
                <CardDescription>
                    Monitor daily restaurant video runs and their processing status
                </CardDescription>
              </CardHeader>
              <CardContent>
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Run Details</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Videos</TableHead>
                          <TableHead>Total Duration</TableHead>
                          <TableHead>Processing Time</TableHead>
                          <TableHead>Cost</TableHead>
                          <TableHead className="w-[100px]">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {processingRuns.map((run) => (
                          <TableRow 
                            key={run.id}
                            className={run.status === 'error' ? 'cursor-pointer hover:bg-red-50' : ''}
                            onClick={() => handleErrorRowClick(run)}
                          >
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <IconVideo className="h-4 w-4 text-primary" />
                        <div>
                                  <p className="font-medium">{run.restaurantName}</p>
                          <p className="text-sm text-muted-foreground">
                                    {run.restaurantLocation} • {format(run.date, 'MMM dd, yyyy')}
                                  </p>
                                  <p className="text-xs text-muted-foreground">
                                    Run ID: {run.runId}
                          </p>
                        </div>
                      </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                {getStatusIcon(run.status)}
                                {getStatusBadge(run)}
                              </div>
                            </TableCell>

                            <TableCell>
                              <div className="text-sm">
                                <div className="font-medium">{run.totalVideos} videos</div>
                                <div className="text-muted-foreground">
                                  {run.videoFiles.slice(0, 2).map(v => v.startTime + "-" + v.endTime).join(", ")}
                                  {run.videoFiles.length > 2 && "..."}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <span className="text-sm">{formatDuration(run.totalDuration)}</span>
                            </TableCell>
                            <TableCell>
                              <span className="text-sm text-gray-900">
                                {run.processingTime || "-"}
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className="text-sm font-medium text-gray-900">
                                {run.cost}
                              </span>
                            </TableCell>
                            <TableCell>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" className="h-8 w-8 p-0">
                                    <span className="sr-only">Open menu</span>
                                    <IconDotsVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  {run.status === 'pending' && (
                                    <DropdownMenuItem onClick={() => startLabeling(run.id)}>
                                      <IconTag className="mr-2 h-4 w-4" />
                                      Start Labeling
                                    </DropdownMenuItem>
                                  )}
                                  {(run.status === 'labeling' || run.status === 'completed') && (
                                    <DropdownMenuItem>
                                      <IconTag className="mr-2 h-4 w-4" />
                                      Label Operators
                                    </DropdownMenuItem>
                                  )}
                                  {run.status === 'completed' && (
                                    <>
                                      <DropdownMenuItem>
                                        <IconEye className="mr-2 h-4 w-4" />
                                        View Results
                                      </DropdownMenuItem>
                                      <DropdownMenuItem>
                                        <IconDownload className="mr-2 h-4 w-4" />
                                        Download Report
                                      </DropdownMenuItem>
                  </>
                )}
                                  {run.status === 'error' && (
                                    <DropdownMenuItem onClick={() => retryRun(run.id)}>
                                      <IconRefresh className="mr-2 h-4 w-4" />
                                      Retry Run
                                    </DropdownMenuItem>
                                  )}
                                  <DropdownMenuItem 
                                    onClick={() => deleteRun(run.id)}
                                    className="text-red-600"
                                  >
                                    <IconTrash className="mr-2 h-4 w-4" />
                                    Delete Run
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
            </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Error Details Dialog */}
      <Dialog open={isErrorDialogOpen} onOpenChange={setIsErrorDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <IconAlertTriangle className="h-5 w-5" />
              {selectedErrorRun && getErrorDetails(selectedErrorRun.errorCode || '').title}
            </DialogTitle>
            <DialogDescription>
              Run ID: {selectedErrorRun?.runId}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">What happened?</h4>
              <p className="text-sm text-gray-600">
                {selectedErrorRun && getErrorDetails(selectedErrorRun.errorCode || '').description}
              </p>
            </div>
            
            <div>
              <h4 className="font-medium text-gray-900 mb-2">How to fix it</h4>
              <p className="text-sm text-gray-600">
                {selectedErrorRun && getErrorDetails(selectedErrorRun.errorCode || '').solution}
              </p>
            </div>
            
            <div className="bg-blue-50 p-3 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-1">Need help?</h4>
              <p className="text-sm text-blue-700 mb-2">
                If you're still having trouble, our support team is here to help.
              </p>
              <div className="space-y-1 text-sm">
                <p><strong>Email:</strong> support@analytics.com</p>
                <p><strong>Phone:</strong> 1-800-ANALYTICS (262-598)</p>
                <p><strong>Hours:</strong> Mon-Fri, 9 AM - 6 PM PST</p>
              </div>
            </div>
            
            <div className="flex gap-2 pt-2">
              <Button 
                variant="outline"
                onClick={() => setIsErrorDialogOpen(false)}
                className="flex-1"
              >
                Close
              </Button>
              <Button 
                onClick={() => {
                  // Simulate retry action
                  console.log('Retrying run:', selectedErrorRun?.id)
                  setIsErrorDialogOpen(false)
                }}
                className="flex-1"
              >
                <IconRefresh className="mr-2 h-4 w-4" />
                Retry Run
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </AppLayout>
    </RequireAuth>
  )
}
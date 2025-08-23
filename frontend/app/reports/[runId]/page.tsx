"use client"

import { useEffect } from 'react'
import { useParams } from 'next/navigation'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

// Detailed transaction data interface
interface TransactionData {
  Date: string
  "Begin Time": string
  "End Time": string
  Transcript: string
  "Complete Transcript?": number
  "Mobile Order?": number
  "Coupon Used?": number
  "Requested More Time?": number
  "Out of Stock Items": string
  "Items Initially Requested": string
  "# of Items Ordered": number
  "# of Chances to Upsell": number
  "Items that Could be Upsold": string
  "# of Upselling Offers Made": number
  "Items Succesfully Upsold": string
  "# of Sucessfull Upselling chances": number
  "# of Times largest Option Offered": number
  "# of Chances to Upsize": number
  "Items in Order that could be Upsized": string
  "# of Upsizing Offers Made": number
  "# of Sucessfull Upsizing chances": number
  "Items Successfully Upsized": string
  "# of Chances to Add-on": number
  "Items in Order that could have Add-Ons": string
  "# of Add-on Offers": number
  "# of Succesful Add-on Offers": number
  "Items with Successful Add-Ons": string
  "Items Ordered After Upsizing, Upselling, and Add-on Offers": string
  "# of Items Ordered After Upselling, Upsizing, and Add-on Offers": number
  "General Feedback": string
  "Response Difficulties": string
  "Reasoning Summary": string
  "GPT Query Price": number
  "GDrive Video FilePath": string
  "GDrive Video Link": string
  "Employee Name": string
}

// Generate sample data based on run ID - in a real app, you'd fetch this from your backend
const generateReportData = (runId: string) => {
  // Extract date from run ID if it follows the RUN-YYMMDD-XXX pattern
  const dateMatch = runId.match(/RUN-(\d{6})-\d{3}/)
  let reportDate = new Date().toLocaleDateString()
  
  if (dateMatch) {
    const dateStr = dateMatch[1]
    const year = 2000 + parseInt(dateStr.substring(0, 2))
    const month = parseInt(dateStr.substring(2, 4)) - 1
    const day = parseInt(dateStr.substring(4, 6))
    reportDate = new Date(year, month, day).toLocaleDateString()
  }
  
  // Generate some realistic sample data
  const addonChances = Math.floor(Math.random() * 5) + 1
  const upsellChances = Math.floor(Math.random() * 3)
  const upsizeChances = Math.floor(Math.random() * 4)
  
  // Generate 50 sample transactions for this run
  const generateTransaction = (index: number): TransactionData => {
    const employees = ["Alice Johnson", "Bob Smith", "Carol Williams", "David Brown", "Eve Davis", "Frank Miller", "Grace Wilson", "Henry Taylor"]
    const items = [
      "Medium Oreo Blizzard, Small Vanilla Cone",
      "Large Chocolate Shake, Burger Combo",
      "Small Strawberry Sundae, Medium Fries",
      "Large Peanut Buster Parfait",
      "Medium Banana Split, Hot Dog",
      "Small Dipped Cone, Chicken Strip Basket",
      "Large Chocolate Blizzard, Onion Rings",
      "Medium Caramel Sundae, Cheeseburger",
      "Small Cotton Candy Blizzard, Fish Sandwich",
      "Large Vanilla Malt, Chicken Combo"
    ]
    
    const hour = 11 + Math.floor(index / 10)
    const minute = (index * 3) % 60
    const duration = Math.floor(Math.random() * 300) + 120 // 2-7 minutes
    const endMinute = (minute + Math.floor(duration / 60)) % 60
    const endHour = hour + Math.floor((minute + Math.floor(duration / 60)) / 60)
    
    const upsellChances = Math.floor(Math.random() * 4)
    const upsizeChances = Math.floor(Math.random() * 3)
    const addonChances = Math.floor(Math.random() * 5) + 1
    
    const itemsOrdered = items[index % items.length]
    
    return {
      Date: reportDate,
      "Begin Time": `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}:00`,
      "End Time": `${endHour.toString().padStart(2, '0')}:${endMinute.toString().padStart(2, '0')}:${(index % 60).toString().padStart(2, '0')}`,
      Transcript: `"Order #${index + 1}: Customer ordered ${itemsOrdered}. Various upselling opportunities were ${Math.random() > 0.5 ? 'offered' : 'missed'} during the interaction."`,
      "Complete Transcript?": Math.random() > 0.1 ? 1 : 0,
      "Mobile Order?": Math.random() > 0.7 ? 1 : 0,
      "Coupon Used?": Math.random() > 0.8 ? 1 : 0,
      "Requested More Time?": Math.random() > 0.9 ? 1 : 0,
      "Out of Stock Items": Math.random() > 0.95 ? "Ice Cream Cake" : "",
      "Items Initially Requested": itemsOrdered,
      "# of Items Ordered": Math.floor(Math.random() * 4) + 1,
      "# of Chances to Upsell": upsellChances,
      "Items that Could be Upsold": upsellChances > 0 ? (Math.random() > 0.5 ? "Blizzard, Shake" : "Burger, Combo") : "",
      "# of Upselling Offers Made": Math.floor(upsellChances * (0.4 + Math.random() * 0.4)),
      "Items Succesfully Upsold": upsellChances > 0 && Math.random() > 0.6 ? (Math.random() > 0.5 ? "Large Blizzard" : "Deluxe Burger") : "",
      "# of Sucessfull Upselling chances": Math.floor(upsellChances * (0.1 + Math.random() * 0.3)),
      "# of Times largest Option Offered": Math.floor(Math.random() * 2),
      "# of Chances to Upsize": upsizeChances,
      "Items in Order that could be Upsized": upsizeChances > 0 ? (Math.random() > 0.5 ? "Medium Blizzard" : "Small Cone") : "",
      "# of Upsizing Offers Made": Math.floor(upsizeChances * (0.5 + Math.random() * 0.3)),
      "# of Sucessfull Upsizing chances": Math.floor(upsizeChances * (0.2 + Math.random() * 0.3)),
      "Items Successfully Upsized": upsizeChances > 0 && Math.random() > 0.7 ? (Math.random() > 0.5 ? "Large Blizzard" : "Medium Cone") : "",
      "# of Chances to Add-on": addonChances,
      "Items in Order that could have Add-Ons": "Ice Cream, Burgers, Shakes",
      "# of Add-on Offers": Math.floor(addonChances * (0.3 + Math.random() * 0.4)),
      "# of Succesful Add-on Offers": Math.floor(addonChances * (0.1 + Math.random() * 0.2)),
      "Items with Successful Add-Ons": Math.random() > 0.7 ? (Math.random() > 0.5 ? "Extra Toppings" : "Dipped Cone") : "",
      "Items Ordered After Upsizing, Upselling, and Add-on Offers": itemsOrdered + (Math.random() > 0.7 ? ", Extra Item" : ""),
      "# of Items Ordered After Upselling, Upsizing, and Add-on Offers": Math.floor(Math.random() * 5) + 1,
      "General Feedback": [
        "Good order accuracy, missed upselling opportunities",
        "Excellent customer service, offered appropriate add-ons",
        "Quick service but could improve suggestive selling",
        "Professional interaction with successful upselling",
        "Standard order taking, some opportunities missed"
      ][Math.floor(Math.random() * 5)],
      "Response Difficulties": Math.random() > 0.8 ? "Audio quality issues" : "Clear transaction",
      "Reasoning Summary": "Transaction analyzed for upselling opportunities and customer service quality",
      "GPT Query Price": 0.02 + Math.random() * 0.08,
      "GDrive Video FilePath": `/content/drive/MyDrive/Video_to_Dashboard Backend/DQ/Processed Video/DQ_${runId}_${index + 1}.mp4`,
      "GDrive Video Link": `https://drive.google.com/file/d/sample${index + 1}/view?usp=sharing`,
      "Employee Name": employees[index % employees.length]
    }
  }
  
  const sampleTransactions: TransactionData[] = Array.from({ length: 50 }, (_, i) => generateTransaction(i))
  
  // Calculate aggregated summary data from all transactions
  const totalUpsellChances = sampleTransactions.reduce((sum, t) => sum + t["# of Chances to Upsell"], 0)
  const totalUpsellOffers = sampleTransactions.reduce((sum, t) => sum + t["# of Upselling Offers Made"], 0)
  const totalUpsellSuccesses = sampleTransactions.reduce((sum, t) => sum + t["# of Sucessfull Upselling chances"], 0)
  
  const totalUpsizeChances = sampleTransactions.reduce((sum, t) => sum + t["# of Chances to Upsize"], 0)
  const totalUpsizeOffers = sampleTransactions.reduce((sum, t) => sum + t["# of Upsizing Offers Made"], 0)
  const totalUpsizeSuccesses = sampleTransactions.reduce((sum, t) => sum + t["# of Sucessfull Upsizing chances"], 0)
  
  const totalAddonChances = sampleTransactions.reduce((sum, t) => sum + t["# of Chances to Add-on"], 0)
  const totalAddonOffers = sampleTransactions.reduce((sum, t) => sum + t["# of Add-on Offers"], 0)
  const totalAddonSuccesses = sampleTransactions.reduce((sum, t) => sum + t["# of Succesful Add-on Offers"], 0)
  
  // Generate detailed item breakdowns matching the reference format
  const upsellItemsDetailed = [
    { item: "Fries", count: Math.floor(totalUpsellSuccesses * 0.35) },
    { item: "Drinks", count: Math.floor(totalUpsellSuccesses * 0.30) },
    { item: "Onion Rings", count: Math.floor(totalUpsellSuccesses * 0.20) },
    { item: "Whopper Junior", count: Math.floor(totalUpsellSuccesses * 0.15) }
  ]
  
  const upsizeItemsDetailed = [
    { item: "Coffee", count: Math.floor(totalUpsizeSuccesses * 0.05) },
    { item: "Hashbrown", count: Math.floor(totalUpsizeSuccesses * 0.10) },
    { item: "Drinks", count: Math.floor(totalUpsizeSuccesses * 0.45) },
    { item: "Large Fries", count: Math.floor(totalUpsizeSuccesses * 0.30) },
    { item: "Chicken fingers (12 piece)", count: Math.floor(totalUpsizeSuccesses * 0.05) },
    { item: "Onion Rings", count: Math.floor(totalUpsizeSuccesses * 0.03) },
    { item: "Frozen strawberry", count: Math.floor(totalUpsizeSuccesses * 0.02) }
  ]
  
  const extraToppingsItemsDetailed = [
    { item: "Cheese", count: Math.floor(totalAddonSuccesses * 0.85) },
    { item: "Bacon", count: Math.floor(totalAddonSuccesses * 0.15) }
  ]

  // Legacy simple items for summary
  const upsellItems = upsellItemsDetailed
  const upsizeItems = upsizeItemsDetailed  
  const addonItems = extraToppingsItemsDetailed

  return {
    runId,
    date: reportDate,
    transactions: sampleTransactions,
    upsellItemsDetailed,
    upsizeItemsDetailed,
    extraToppingsItemsDetailed,
    summary: {
      upsell: {
        chances: totalUpsellChances,
        offers: totalUpsellOffers,
        offerRate: totalUpsellChances > 0 ? (totalUpsellOffers / totalUpsellChances * 100) : 0,
        successes: totalUpsellSuccesses,
        conversionRate: totalUpsellOffers > 0 ? (totalUpsellSuccesses / totalUpsellOffers * 100) : 0,
        items: upsellItems,
        total: totalUpsellSuccesses
      },
      upsize: {
        chances: totalUpsizeChances,
        offers: totalUpsizeOffers,
        offerRate: totalUpsizeChances > 0 ? (totalUpsizeOffers / totalUpsizeChances * 100) : 0,
        successes: totalUpsizeSuccesses,
        conversionRate: totalUpsizeOffers > 0 ? (totalUpsizeSuccesses / totalUpsizeOffers * 100) : 0,
        items: upsizeItems,
        total: totalUpsizeSuccesses
      },
      addon: {
        chances: totalAddonChances,
        offers: totalAddonOffers,
        offerRate: totalAddonChances > 0 ? (totalAddonOffers / totalAddonChances * 100) : 0,
        successes: totalAddonSuccesses,
        conversionRate: totalAddonOffers > 0 ? (totalAddonSuccesses / totalAddonOffers * 100) : 0,
        items: addonItems,
        total: totalAddonSuccesses
      }
    }
  }
}

export default function ReportPage() {
  const params = useParams()
  const runId = params.runId as string

  useEffect(() => {
    const generatePDF = () => {
      const reportData = generateReportData(runId)
      const pdf = new jsPDF('landscape', 'pt', 'a4')
      
      // Page settings
      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const margin = 40
      
      // Header
      pdf.setFontSize(16)
      pdf.setFont('helvetica', 'bold')
      pdf.text("Upselling Performance Report", margin, 30)
      
      pdf.setFontSize(10)
      pdf.setFont('helvetica', 'normal')
      pdf.text(`Run ID: ${reportData.runId}`, margin, 50)
      pdf.text(`Generated: ${reportData.date}`, margin, 65)
      
      // Detailed transaction table
      const headers = [
        'Date', 'Begin Time', 'End Time', 'Items Ordered', '# Items', 
        'Upsell Chances', 'Upsell Offers', 'Upsell Success',
        'Upsize Chances', 'Upsize Offers', 'Upsize Success',
        'Add-on Chances', 'Add-on Offers', 'Add-on Success',
        'Employee', 'General Feedback'
      ]
      
      const tableData = reportData.transactions.map(t => [
        t.Date,
        t["Begin Time"],
        t["End Time"],
        t["Items Initially Requested"],
        t["# of Items Ordered"],
        t["# of Chances to Upsell"],
        t["# of Upselling Offers Made"],
        t["# of Sucessfull Upselling chances"],
        t["# of Chances to Upsize"],
        t["# of Upsizing Offers Made"],
        t["# of Sucessfull Upsizing chances"],
        t["# of Chances to Add-on"],
        t["# of Add-on Offers"],
        t["# of Succesful Add-on Offers"],
        t["Employee Name"],
        t["General Feedback"].substring(0, 60) + "..." // Truncate for space
      ])
      
      autoTable(pdf, {
        startY: 85,
        head: [headers],
        body: tableData,
        theme: 'grid',
        styles: { fontSize: 7, cellPadding: 2 },
        headStyles: { fillColor: [220, 220, 220], textColor: [0, 0, 0] },
        columnStyles: {
          15: { cellWidth: 100 } // Feedback column wider
        }
      })
      
      let currentY = (pdf as any).lastAutoTable.finalY + 30
      
      // Summary Section
      pdf.setFontSize(14)
      pdf.setFont('helvetica', 'bold')
      pdf.text("Summary Report", margin, currentY)
      currentY += 25
      
      // Summary Table
      const summaryHeaders = ['Category', 'Chances', 'Offers Made', 'Offer Rate', 'Successful', 'Conversion Rate', 'Items', 'Total']
      const summaryData = [
        [
          'Upsell Summary',
          reportData.summary.upsell.chances.toString(),
          reportData.summary.upsell.offers.toString(),
          `${reportData.summary.upsell.offerRate.toFixed(1)}%`,
          reportData.summary.upsell.successes.toString(),
          `${reportData.summary.upsell.conversionRate.toFixed(1)}%`,
          'Items Suggestively Upsold',
          reportData.summary.upsell.total.toString()
        ],
        [
          'Upsize Summary',
          reportData.summary.upsize.chances.toString(),
          reportData.summary.upsize.offers.toString(),
          `${reportData.summary.upsize.offerRate.toFixed(1)}%`,
          reportData.summary.upsize.successes.toString(),
          `${reportData.summary.upsize.conversionRate.toFixed(1)}%`,
          'Items Suggestively Upsized to Large',
          reportData.summary.upsize.total.toString()
        ],
        [
          'Extra Toppings / Add-Ons Summary',
          reportData.summary.addon.chances.toString(),
          reportData.summary.addon.offers.toString(),
          `${reportData.summary.addon.offerRate.toFixed(1)}%`,
          reportData.summary.addon.successes.toString(),
          `${reportData.summary.addon.conversionRate.toFixed(1)}%`,
          'Extra Toppings Suggestively Added',
          reportData.summary.addon.total.toString()
        ]
      ]
      
      autoTable(pdf, {
        startY: currentY,
        head: [summaryHeaders],
        body: summaryData,
        theme: 'striped',
        styles: { fontSize: 9, cellPadding: 4 },
        headStyles: { fillColor: [100, 100, 100], textColor: [255, 255, 255], fontStyle: 'bold' },
        columnStyles: {
          0: { cellWidth: 120, fontStyle: 'bold' }, // Category column
          1: { halign: 'center', cellWidth: 60 },   // Chances
          2: { halign: 'center', cellWidth: 70 },   // Offers Made
          3: { halign: 'center', cellWidth: 70 },   // Offer Rate
          4: { halign: 'center', cellWidth: 70 },   // Successful
          5: { halign: 'center', cellWidth: 80 },   // Conversion Rate
          6: { cellWidth: 150 },                    // Items description
          7: { halign: 'center', cellWidth: 50 }    // Total
        }
      })
      
      currentY = (pdf as any).lastAutoTable.finalY + 20
      
      // Check if we need a new page for detailed tables
      if (currentY > pageHeight - 300) {
        pdf.addPage()
        currentY = 40
      }
      
      // Upsell Table
      const upsellTableData = [
        // Header row with merged cells for metrics
        ['', '', '', '7/1/2025', '', '', '', '6/30/2025', '', '', ''],
        ['Upsell', 'Count', 'Accuracy', 'Offer %', 'Conversion', 'Count', 'Accuracy', 'Offer %', 'Conversion'],
        ['# of chances upsell', reportData.summary.upsell.chances.toString(), '', '', '', reportData.summary.upsell.chances.toString(), '69%', '', ''],
        ['# of offers made to upsell', reportData.summary.upsell.offers.toString(), '', '35%', '', reportData.summary.upsell.offers.toString(), '85%', '54%', ''],
        ['# of offers that were successful', reportData.summary.upsell.successes.toString(), '', '', '16%', reportData.summary.upsell.successes.toString(), '93%', '', '33%'],
        ['', '', '', '', '', '', '', '', ''],
        ['Items Suggestively Upsold', 'Count', '', '', '', 'Count', '', '', ''],
        ...reportData.upsellItemsDetailed.map(item => [item.item, item.count.toString(), '', '', '', item.count.toString(), '', '', '']),
        ['Total', reportData.summary.upsell.successes.toString(), '', '', '', reportData.summary.upsell.successes.toString(), '', '', '']
      ]
      
      autoTable(pdf, {
        startY: currentY,
        body: upsellTableData,
        theme: 'grid',
        styles: { fontSize: 8, cellPadding: 2 },
        columnStyles: {
          0: { cellWidth: 150 },
          1: { cellWidth: 40, halign: 'center' },
          2: { cellWidth: 50, halign: 'center' },
          3: { cellWidth: 40, halign: 'center' },
          4: { cellWidth: 50, halign: 'center' },
          5: { cellWidth: 40, halign: 'center' },
          6: { cellWidth: 50, halign: 'center' },
          7: { cellWidth: 40, halign: 'center' },
          8: { cellWidth: 50, halign: 'center' }
        },
        didParseCell: function(data) {
          // Style header rows
          if (data.row.index === 0 || data.row.index === 1) {
            data.cell.styles.fillColor = [255, 192, 203] // Light pink
            data.cell.styles.fontStyle = 'bold'
          }
          // Style item header row
          if (data.row.index === 6) {
            data.cell.styles.fillColor = [255, 235, 59] // Yellow
            data.cell.styles.fontStyle = 'bold'
          }
          // Style total row
          if (data.row.index === upsellTableData.length - 1) {
            data.cell.styles.fillColor = [255, 235, 59] // Yellow
            data.cell.styles.fontStyle = 'bold'
          }
        }
      })
      
      currentY = (pdf as any).lastAutoTable.finalY + 20
      
      // Upsize Table
      const upsizeTableData = [
        ['', '', '', '7/1/2025', '', '', '', '6/30/2025', '', '', ''],
        ['Upsize', 'Count', 'Accuracy', 'Offer %', 'Conversion', 'Count', 'Accuracy', 'Offer %', 'Conversion'],
        ['# of chances to upsize', reportData.summary.upsize.chances.toString(), '', '', '', reportData.summary.upsize.chances.toString(), '75%', '', ''],
        ['# of offers made to upsize', reportData.summary.upsize.offers.toString(), '', '69%', '', reportData.summary.upsize.offers.toString(), '89%', '81%', ''],
        ['# of successful upsize offers made', reportData.summary.upsize.successes.toString(), '', '', '40%', reportData.summary.upsize.successes.toString(), '92%', '', '50%'],
        ['', '', '', '', '', '', '', '', ''],
        ['Items Suggestively upsized to large', 'Count', '', '', '', 'Count', '', '', ''],
        ...reportData.upsizeItemsDetailed.map(item => [item.item, item.count.toString(), '', '', '', item.count.toString(), '', '', '']),
        ['Total', reportData.summary.upsize.successes.toString(), '', '', '', reportData.summary.upsize.successes.toString(), '', '', '']
      ]
      
      autoTable(pdf, {
        startY: currentY,
        body: upsizeTableData,
        theme: 'grid',
        styles: { fontSize: 8, cellPadding: 2 },
        columnStyles: {
          0: { cellWidth: 150 },
          1: { cellWidth: 40, halign: 'center' },
          2: { cellWidth: 50, halign: 'center' },
          3: { cellWidth: 40, halign: 'center' },
          4: { cellWidth: 50, halign: 'center' },
          5: { cellWidth: 40, halign: 'center' },
          6: { cellWidth: 50, halign: 'center' },
          7: { cellWidth: 40, halign: 'center' },
          8: { cellWidth: 50, halign: 'center' }
        },
        didParseCell: function(data) {
          // Style header rows
          if (data.row.index === 0 || data.row.index === 1) {
            data.cell.styles.fillColor = [255, 192, 203] // Light pink
            data.cell.styles.fontStyle = 'bold'
          }
          // Style item header row
          if (data.row.index === 6) {
            data.cell.styles.fillColor = [255, 235, 59] // Yellow
            data.cell.styles.fontStyle = 'bold'
          }
          // Style total row
          if (data.row.index === upsizeTableData.length - 1) {
            data.cell.styles.fillColor = [255, 235, 59] // Yellow
            data.cell.styles.fontStyle = 'bold'
          }
        }
      })
      
      currentY = (pdf as any).lastAutoTable.finalY + 20
      
      // Extra Toppings Table
      const extraToppingsTableData = [
        ['', '', '', '7/1/2025', '', '', '', '6/30/2025', '', '', ''],
        ['Extra Toppings', 'Count', 'Accuracy', 'Offer %', 'Conversion', 'Count', 'Accuracy', 'Offer %', 'Conversion'],
        ['# of chances to add extra toppings', reportData.summary.addon.chances.toString(), '', '', '', reportData.summary.addon.chances.toString(), '', '', ''],
        ['# of offers made to add extra toppings', reportData.summary.addon.offers.toString(), '', '', '', reportData.summary.addon.offers.toString(), '0.99', '', ''],
        ['# of successful extra toppings offer', reportData.summary.addon.successes.toString(), '', '', '50%', reportData.summary.addon.successes.toString(), '0.99', '', '74%'],
        ['', '', '', '', '', '', '', '', ''],
        ['Extra Toppings suggestively added', 'Count', '', '', '', 'Count', '', '', ''],
        ...reportData.extraToppingsItemsDetailed.map(item => [item.item, item.count.toString(), '', '', '', item.count.toString(), '', '', '']),
        ['Total', reportData.summary.addon.successes.toString(), '', '', '', reportData.summary.addon.successes.toString(), '', '', '']
      ]
      
      autoTable(pdf, {
        startY: currentY,
        body: extraToppingsTableData,
        theme: 'grid',
        styles: { fontSize: 8, cellPadding: 2 },
        columnStyles: {
          0: { cellWidth: 150 },
          1: { cellWidth: 40, halign: 'center' },
          2: { cellWidth: 50, halign: 'center' },
          3: { cellWidth: 40, halign: 'center' },
          4: { cellWidth: 50, halign: 'center' },
          5: { cellWidth: 40, halign: 'center' },
          6: { cellWidth: 50, halign: 'center' },
          7: { cellWidth: 40, halign: 'center' },
          8: { cellWidth: 50, halign: 'center' }
        },
        didParseCell: function(data) {
          // Style header rows
          if (data.row.index === 0 || data.row.index === 1) {
            data.cell.styles.fillColor = [255, 192, 203] // Light pink
            data.cell.styles.fontStyle = 'bold'
          }
          // Style item header row
          if (data.row.index === 6) {
            data.cell.styles.fillColor = [255, 235, 59] // Yellow
            data.cell.styles.fontStyle = 'bold'
          }
          // Style total row
          if (data.row.index === extraToppingsTableData.length - 1) {
            data.cell.styles.fillColor = [255, 235, 59] // Yellow
            data.cell.styles.fontStyle = 'bold'
          }
        }
      })
      
      // Add footer
      pdf.setFontSize(8)
      pdf.setFont('helvetica', 'italic')
      const footerText = `Report generated on ${new Date().toLocaleString()}`
      const footerWidth = pdf.getStringUnitWidth(footerText) * 8 / pdf.internal.scaleFactor
      pdf.text(footerText, (pageWidth - footerWidth) / 2, pageHeight - 20)
      
      // Download the PDF
      pdf.save(`upselling-report-${runId}.pdf`)
      
      // Close the window after a short delay
      setTimeout(() => {
        window.close()
      }, 1000)
    }

    // Generate PDF immediately when component mounts
    generatePDF()
  }, [runId])

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <h2 className="text-xl font-semibold text-gray-700">Generating Report...</h2>
        <p className="text-gray-500 mt-2">Your PDF report for {runId} is being prepared.</p>
        <p className="text-sm text-gray-400 mt-1">This window will close automatically.</p>
      </div>
    </div>
  )
}

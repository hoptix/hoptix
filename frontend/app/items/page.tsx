"use client"

import { useState } from 'react'
import { AppLayout } from '@/components/app-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { 
  IconPlus, 
  IconTrash, 
  IconEdit,
  IconSearch, 
  IconCurrencyDollar
} from '@tabler/icons-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

// Item interface based on the provided data structure
interface MenuItem {
  id: string
  name: string
  sizes: string[]
  orderedItemsCount: number
  upselling: string
  upsizing: string
  addOn: string
  cost: number
}

// Sample data based on the provided list
const initialItems: MenuItem[] = [
  {
    id: '1',
    name: 'Sundae [Size: Small]',
    sizes: ['Small'],
    orderedItemsCount: 1,
    upselling: '2 (valid items) for $5. Valid items: Small Sundae, Pretzel, Chilli dog or any size drink',
    upsizing: 'Large Sundae (1)',
    addOn: 'Whipped Cream/Nuts/Sprinkles',
    cost: 3.99
  },
  {
    id: '2',
    name: 'Sundae [Size: Medium, Large]',
    sizes: ['Medium', 'Large'],
    orderedItemsCount: 1,
    upselling: '0',
    upsizing: 'Large Sundae (1)',
    addOn: 'Whipped Cream/Nuts/Sprinkles',
    cost: 4.99
  },
  {
    id: '3', 
    name: 'Chips',
    sizes: ['None'],
    orderedItemsCount: 1,
    upselling: '0',
    upsizing: 'Pretzel Sticks (1)',
    addOn: '0',
    cost: 2.49
  },
  {
    id: '4',
    name: 'Pretzel sticks',
    sizes: ['None'],
    orderedItemsCount: 1,
    upselling: '2 (valid items) for $5. Valid items: Small Sundae, Pretzel, Chilli dog or any size drink',
    upsizing: '0',
    addOn: '0',
    cost: 2.99
  },
  {
    id: '5',
    name: 'Drink',
    sizes: ['Small', 'Medium', 'Large'],
    orderedItemsCount: 1,
    upselling: '2 (valid items) for $5. Valid items: Small Sundae, Pretzel, Chilli dog or any size drink',
    upsizing: 'Large Drink (1)',
    addOn: '0',
    cost: 1.99
  },
  {
    id: '6',
    name: 'Chilli dog',
    sizes: ['None'],
    orderedItemsCount: 1,
    upselling: '2 (valid items) for $5. Valid items: Small Sundae, Pretzel, Chilli dog or any size drink',
    upsizing: '0',
    addOn: '0',
    cost: 3.49
  },
  {
    id: '7',
    name: 'Cone',
    sizes: ['Small', 'Medium', 'Large'],
    orderedItemsCount: 1,
    upselling: '0',
    upsizing: 'Large Cone (1)',
    addOn: 'Sprinkles',
    cost: 2.99
  },
  {
    id: '8',
    name: 'Dipped Cone',
    sizes: ['Small', 'Medium', 'Large'],
    orderedItemsCount: 1,
    upselling: '0',
    upsizing: 'Large Dipped Cone (1)',
    addOn: 'Double Dip',
    cost: 3.49
  },
  {
    id: '9',
    name: 'Blizzard',
    sizes: ['Small', 'Medium', 'Large'],
    orderedItemsCount: 1,
    upselling: '0',
    upsizing: 'Large Blizzard (1)',
    addOn: 'Primary Topping/Ingredient',
    cost: 4.99
  },
  {
    id: '10',
    name: 'Fries',
    sizes: ['Kids', 'Regular', 'Large', 'Basket'],
    orderedItemsCount: 1,
    upselling: '0',
    upsizing: 'Large Fries (1)',
    addOn: '0',
    cost: 2.99
  },
  {
    id: '11',
    name: 'Original Cheeseburger',
    sizes: ['Single', 'Double', 'Triple'],
    orderedItemsCount: 1,
    upselling: '[Drink (1) and/or Fries (1) and/or Sundae/Blizzard (1)] OR [Meal Item (See Meal table)]',
    upsizing: '0',
    addOn: '0',
    cost: 5.99
  },
  {
    id: '12',
    name: 'Onion Rings',
    sizes: ['Regular', 'Large'],
    orderedItemsCount: 1,
    upselling: '0',
    upsizing: 'Large Onion Rings (1)',
    addOn: '0',
    cost: 3.49
  }
]

export default function ItemsPage() {
  const [items, setItems] = useState<MenuItem[]>(initialItems)
  const [searchTerm, setSearchTerm] = useState('')
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [deleteItemId, setDeleteItemId] = useState<string | null>(null)
  const [newItem, setNewItem] = useState<Omit<MenuItem, 'id'>>({
    name: '',
    sizes: [],
    orderedItemsCount: 1,
    upselling: '',
    upsizing: '',
    addOn: '',
    cost: 0
  })

  const filteredItems = items.filter(item =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleAddItem = () => {
    const item: MenuItem = {
      ...newItem,
      id: Date.now().toString(),
    }
    setItems([...items, item])
    setNewItem({
      name: '',
      sizes: [],
      orderedItemsCount: 1,
      upselling: '',
      upsizing: '',
      addOn: '',
      cost: 0
    })
    setIsAddDialogOpen(false)
  }

  const handleDeleteItem = (id: string) => {
    setItems(items.filter(item => item.id !== id))
    setDeleteItemId(null)
  }

  const handleSizesChange = (sizesString: string) => {
    const sizes = sizesString.split(',').map(s => s.trim()).filter(s => s.length > 0)
    setNewItem({ ...newItem, sizes })
  }

  return (
    <AppLayout>
      <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
        <div className="min-h-[100vh] flex-1 rounded-xl bg-muted/50 md:min-h-min">
          <div className="p-6">
            {/* Header */}
            <div className="mb-6">
              <h1 className="text-3xl font-bold">Menu Items Management</h1>
              <p className="text-muted-foreground mt-2">
                Manage your fast food chain menu items, pricing, and upselling options
              </p>
            </div>

            {/* Controls */}
            <div className="flex flex-col gap-4 mb-6 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative flex-1 max-w-sm">
                <IconSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search items..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              
              <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <IconPlus className="mr-2 h-4 w-4" />
                    Add Item
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>Add New Menu Item</DialogTitle>
                    <DialogDescription>
                      Create a new menu item with pricing and upselling options.
                    </DialogDescription>
                  </DialogHeader>
                  
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="name">Item Name</Label>
                        <Input
                          id="name"
                          value={newItem.name}
                          onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                          placeholder="e.g., Burger"
                        />
                      </div>
                      <div>
                        <Label htmlFor="cost">Cost ($)</Label>
                        <div className="relative">
                          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">$</span>
                          <Input
                            id="cost"
                            type="number"
                            step="0.01"
                            value={newItem.cost}
                            onChange={(e) => setNewItem({ ...newItem, cost: parseFloat(e.target.value) || 0 })}
                            placeholder="0.00"
                            className="pl-8"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="sizes">Sizes (comma-separated)</Label>
                        <Input
                          id="sizes"
                          value={newItem.sizes.join(', ')}
                          onChange={(e) => handleSizesChange(e.target.value)}
                          placeholder="Small, Medium, Large"
                        />
                      </div>
                      <div>
                        <Label htmlFor="count">Ordered Items Count</Label>
                        <Input
                          id="count"
                          type="number"
                          value={newItem.orderedItemsCount}
                          onChange={(e) => setNewItem({ ...newItem, orderedItemsCount: parseInt(e.target.value) || 1 })}
                        />
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="upselling">Upselling Opportunities</Label>
                      <Textarea
                        id="upselling"
                        value={newItem.upselling}
                        onChange={(e) => setNewItem({ ...newItem, upselling: e.target.value })}
                        placeholder="Describe upselling opportunities..."
                        rows={2}
                      />
                    </div>

                    <div>
                      <Label htmlFor="upsizing">Upsizing Options</Label>
                      <Textarea
                        id="upsizing"
                        value={newItem.upsizing}
                        onChange={(e) => setNewItem({ ...newItem, upsizing: e.target.value })}
                        placeholder="Describe upsizing options..."
                        rows={2}
                      />
                    </div>

                    <div>
                      <Label htmlFor="addOn">Add-on Options</Label>
                      <Textarea
                        id="addOn"
                        value={newItem.addOn}
                        onChange={(e) => setNewItem({ ...newItem, addOn: e.target.value })}
                        placeholder="Describe add-on options..."
                        rows={2}
                      />
                    </div>
                  </div>

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleAddItem} disabled={!newItem.name.trim()}>
                      Add Item
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            {/* Items Table */}
            <Card>
              <CardHeader>
                <CardTitle>Menu Items ({filteredItems.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Item</TableHead>
                        <TableHead>Sizes</TableHead>
                        <TableHead>Cost</TableHead>
                        <TableHead>Count</TableHead>
                        <TableHead>Upselling Chance</TableHead>
                        <TableHead>Upsizing Chance</TableHead>
                        <TableHead>Add-on Chance</TableHead>
                        <TableHead className="w-20">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredItems.map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-medium">{item.name}</TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {item.sizes.map((size, index) => (
                                <Badge key={index} variant="secondary" className="text-xs">
                                  {size}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                          <TableCell className="font-mono">${item.cost.toFixed(2)}</TableCell>
                          <TableCell className="text-center">{item.orderedItemsCount}</TableCell>
                          <TableCell className="max-w-xs">
                            <div className="truncate" title={item.upselling}>
                              {item.upselling || 'None'}
                            </div>
                          </TableCell>
                          <TableCell className="max-w-xs">
                            <div className="truncate" title={item.upsizing}>
                              {item.upsizing || 'None'}
                            </div>
                          </TableCell>
                          <TableCell className="max-w-xs">
                            <div className="truncate" title={item.addOn}>
                              {item.addOn || 'None'}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => setDeleteItemId(item.id)}
                              >
                                <IconTrash className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                      {filteredItems.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                            No items found
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteItemId} onOpenChange={() => setDeleteItemId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Item</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this menu item? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteItemId && handleDeleteItem(deleteItemId)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppLayout>
  )
}

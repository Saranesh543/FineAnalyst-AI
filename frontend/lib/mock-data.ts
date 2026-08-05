export const MOCK_DATA_SOURCES = [
  {
    id: "ds-1",
    name: "ecommerce.db",
    type: "SQLite",
    lastUpdated: "2 mins ago",
    status: "connected",
    icon: "database"
  },
  {
    id: "ds-2",
    name: "sales_data.csv",
    type: "CSV",
    lastUpdated: "1 hour ago",
    status: "connected",
    icon: "file-spreadsheet"
  },
  {
    id: "ds-3",
    name: "finance.xlsx",
    type: "Excel",
    lastUpdated: "3 hours ago",
    status: "connected",
    icon: "file-excel"
  },
  {
    id: "ds-4",
    name: "marketing_data.db",
    type: "SQLite",
    lastUpdated: "1 day ago",
    status: "connected",
    icon: "database"
  }
];

export const MOCK_HISTORY_TODAY = [
  { id: "h-1", title: "Revenue trend analysis", time: "10:30 AM" },
  { id: "h-2", title: "Top 10 customers by revenue", time: "09:15 AM" },
  { id: "h-3", title: "Sales by region this quarter", time: "08:45 AM" },
  { id: "h-4", title: "Product performance comp...", time: "07:30 AM" },
  { id: "h-5", title: "Monthly profit analysis", time: "07:10 AM" }
];

export const MOCK_HISTORY_YESTERDAY = [
  { id: "h-6", title: "Inventory analysis", time: "Yesterday" },
  { id: "h-7", title: "Customer retention rate", time: "Yesterday" },
  { id: "h-8", title: "Marketing campaign ROI", time: "Yesterday" }
];

export const MOCK_HISTORY_LAST_7_DAYS = [
  { id: "h-9", title: "Quarterly sales report", time: "2 days ago" },
  { id: "h-10", title: "Year over year growth", time: "3 days ago" },
  { id: "h-11", title: "Top products by category", time: "5 days ago" }
];

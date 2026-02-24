# EQUIPOS 6.0 - Modern UI "Tierra & Asfalto"

## 🎨 Quick Visual Reference

### Color Palette
```
Primary Colors:
  🟨 #F59E0B  Caterpillar Yellow/Amber (Primary actions, highlights)
  ⬛ #1F2937  Dark Asphalt (Sidebar background)
  ⬜ #FFFFFF  White (Cards, inputs)
  🔳 #F3F4F6  Concrete Gray (Page background)

Accent Colors:
  🔵 #3B82F6  Blue (Revenue, secondary actions)
  🟢 #10B981  Green (Success, profit)
  🟣 #6366F1  Purple (Metrics, occupation)

Status Colors:
  ✅ Paid:    #DCFCE7 / #166534
  ⏰ Pending: #FEF3C7 / #92400E
  ❌ Overdue: #FEE2E2 / #991B1B
```

### Layout Structure
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  ┌─────────┐  ┌───────────────────────────────────┐ │
│  │         │  │ 🏠 Dashboard    [Search box...]   │ │
│  │   Z     │  ├───────────────────────────────────┤ │
│  │ ZOEC    │  │                                   │ │
│  │ CIVIL   │  │  🎯 KPI Cards Grid (4 columns)   │ │
│  │         │  │                                   │ │
│  │────────│  │  📊 Table with Status Badges      │ │
│  │         │  │                                   │ │
│  │ 🏠      │  │                                   │ │
│  │ 🚜      │  │                                   │ │
│  │ 💰      │  │                                   │ │
│  │ 👤      │  │                                   │ │
│  │         │  │                                   │ │
│  │────────│  │                                   │ │
│  │ ⚙️       │  │                                   │ │
│  │ v6.0    │  │                                   │ │
│  └─────────┘  └───────────────────────────────────┘ │
│                                                      │
└──────────────────────────────────────────────────────┘
   260px         TopBar 70px + Content Area
```

## 📦 What's New in Version 6.0

### 1. **Modern Visual Design**
- ✨ Light theme with professional color palette
- ✨ "Tierra & Asfalto" design language (Construction/Industrial aesthetic)
- ✨ Sidebar navigation (replacing tabs)
- ✨ Improved visual hierarchy and spacing

### 2. **New UI Components**
- 🎴 **StatCard**: KPI cards with icons, values, and accent bars
- 🏷️ **StatusBadge**: Pill-shaped status indicators
- 🔘 **SidebarButton**: Navigation buttons with icons and states
- 📋 **TopBar**: Page header with title and search
- 🗂️ **ModernCard**: White card container with shadow
- 🔳 **ModernButton**: Styled buttons with variants

### 3. **SVG Icon System**
- 🎨 20+ embedded icons
- 🌈 Color-parameterized (adapt to any theme)
- 🚀 No external dependencies
- 📝 Easy to extend

### 4. **Improved Dashboard**
- 📊 4 main KPI cards with color-coded icons:
  - 💵 Ingresos Totales (Blue)
  - ⏰ Pendiente Cobro (Amber)
  - 📈 Utilidad Neta (Green)
  - ⚙️ Ocupación Equipos (Purple)
- 🔝 Top Equipment & Top Operator cards
- 🎯 Modern activity table with status badges
- 🔍 Clean filter interface

## 🚀 Quick Start

### For Developers

1. **Import modern theme in your view:**
```python
from app_theme_modern import ModernTheme
from ui_components import StatCard, StatusBadge, ModernCard
from icons import get_icon
```

2. **Apply theme to window:**
```python
self.setStyleSheet(ModernTheme.get_stylesheet())
```

3. **Use modern components:**
```python
# Create a KPI card
kpi = StatCard(
    title="Total Sales",
    value="$250,000",
    icon_name="attach_money",
    accent_color=ModernTheme.COLORS['primary']
)

# Create a status badge
badge = StatusBadge()
badge.setPaid()  # or setPending() / setOverdue()

# Create a modern card container
card = ModernCard(title="My Data")
card.add_widget(my_widget)
```

### For Users

1. Launch the application
2. Notice the new sidebar on the left with yellow "Z" logo
3. Click navigation buttons to switch between views:
   - 🏠 Dashboard
   - 🚜 Alquileres
   - 💰 Gastos
   - 👤 Pagos Operadores
4. Use filters to refine data
5. Look for color-coded status badges in tables

## 📁 File Structure

```
EQUIPOS_6.0/
├── icons.py                    # SVG icon system
├── app_theme_modern.py         # Color palette & QSS styles
├── ui_components.py            # Reusable modern components
├── app_gui_qt.py              # Main window (updated)
├── dashboard_tab.py           # Dashboard view (updated)
├── main_qt.py                 # Entry point (updated)
├── IMPLEMENTATION_GUIDE.md    # Detailed technical guide
└── TEST_MODERN_UI.md          # Testing checklist
```

## 🎯 Key Features

### Design System
- ✅ Consistent color palette
- ✅ Reusable components
- ✅ Typography system
- ✅ Spacing guidelines
- ✅ Modern QSS styles

### Components
- ✅ SidebarButton with hover/active states
- ✅ StatCard with icons and accent colors
- ✅ StatusBadge (pill-shaped)
- ✅ TopBar with title and search
- ✅ ModernCard container
- ✅ ModernButton variants

### Icons
- ✅ 20+ SVG icons embedded
- ✅ Color-parameterized
- ✅ Dashboard, agriculture, payments, etc.
- ✅ Easy to add more

## 📊 Example Screenshots

*(To be added after manual testing with PyQt6)*

## 🔧 Customization

### Change Colors
Edit `app_theme_modern.py`:
```python
COLORS = {
    'primary': '#YOUR_COLOR',  # Change primary color
    # ... other colors
}
```

### Add New Icon
Edit `icons.py`:
```python
svg_templates = {
    'your_icon': f'''<svg...>{color}</svg>''',
}
```

### Create Custom Component
Use existing components as templates in `ui_components.py`

## 🧪 Testing

### Automated ✅
- [x] Syntax validation
- [x] Import checks
- [x] Code review
- [x] CodeQL security scan (0 alerts)

### Manual (Requires PyQt6)
- [ ] Visual appearance
- [ ] Navigation functionality
- [ ] Data updates
- [ ] Responsive behavior

See `TEST_MODERN_UI.md` for detailed testing checklist.

## 📚 Documentation

- **IMPLEMENTATION_GUIDE.md**: Complete technical implementation details
- **TEST_MODERN_UI.md**: Testing checklist and procedures
- **This README**: Quick overview and getting started

## 🔒 Security

- ✅ CodeQL scan passed (0 alerts)
- ✅ No external dependencies for icons
- ✅ All code reviewed
- ✅ No security vulnerabilities detected

## 🤝 Compatibility

- ✅ Python 3.10+
- ✅ PyQt6
- ✅ Windows/Linux
- ✅ Firebase integration preserved
- ✅ All existing functionality maintained

## 📝 Notes

- The redesign maintains all existing functionality
- Business logic and Firebase integration unchanged
- Can be deployed alongside existing version
- Future views can adopt modern components gradually

## 🎓 Resources

- [PyQt6 Documentation](https://doc.qt.io/qt-6/)
- [Material Design Principles](https://material.io/design)
- [Color Psychology](https://www.colorpsychology.org/)

## 📞 Support

For issues or questions:
1. Check IMPLEMENTATION_GUIDE.md for technical details
2. Review TEST_MODERN_UI.md for testing procedures
3. Consult code comments in source files

---

**Version**: 6.0  
**Theme**: "Tierra & Asfalto"  
**Status**: ✅ Ready for Testing  
**Last Updated**: February 2026

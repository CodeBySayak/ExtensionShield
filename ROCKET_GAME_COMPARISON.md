# Rocket Game Implementation Comparison

## Overview
Comparison between the **reference version** (7 commits behind, working correctly) and the **current version** for the route `/scan/progress/:scanId`.

---

## Key Differences: ScanProgressPage.jsx

### **Reference Version (Simple & Working)**
- **Lines**: 184 lines
- **Dependencies**: Minimal - only basic React hooks, Router, Button, RocketGame, ScanContext
- **State Management**: Simple - only 3 state variables:
  - `extensionLogo`
  - `scanComplete`
  - `userExited`

### **Current Version (Complex)**
- **Lines**: 467 lines (2.5x larger!)
- **Dependencies**: Many additional imports:
  - `realScanService` - API service calls
  - `ScanHUD` - Additional UI component
  - `Dialog` components - Modal system
  - More complex error handling

- **State Management**: 10+ state variables:
  - `extensionLogo`
  - `extensionName` ⚠️ NEW
  - `scanComplete`
  - `userExited`
  - `showErrorModal` ⚠️ NEW
  - `showCompletionModal` ⚠️ NEW
  - `errorMessage` ⚠️ NEW
  - `gameStarted` ⚠️ NEW
  - `gameStats` ⚠️ NEW
  - `gameOver` ⚠️ NEW
  - `scanProgress` ⚠️ NEW
  - `isMobile` ⚠️ NEW

---

## Critical Differences

### 1. **Game Display Logic**

#### Reference Version (Simple):
```javascript
const shouldShowGame = 
  (isScanning && currentExtensionId === scanId) || 
  (scanComplete && !userExited);
```

#### Current Version (Complex):
```javascript
const shouldShowGame = 
  (isScanning && currentExtensionId === scanId) || 
  (scanComplete && !userExited) ||
  (gameStarted && !userExited) || 
  (currentExtensionId === scanId && !userExited) ||
  (scanId && !userExited); // Default: show game if we have a scanId
```

**Issue**: The current version has multiple fallback conditions that might cause the game to show when it shouldn't, or hide when it should show.

---

### 2. **RocketGame Component Props**

#### Reference Version:
```javascript
<RocketGame 
  isActive={true} 
  statusLabel={
    scanComplete 
      ? "Scan complete! Keep playing or click 'View Results' above." 
      : "Running the scan... Play a game till then!"
  }
/>
```

#### Current Version:
```javascript
<RocketGame 
  isActive={true} 
  statusLabel={...}
  onStatsUpdate={(stats) => {
    setGameStats(stats);
    if (stats.gameOver !== undefined) {
      setGameOver(stats.gameOver);
    }
  }}
  showScoreboard={false}
/>
```

**Difference**: Current version adds `onStatsUpdate` callback and `showScoreboard` prop.

---

### 3. **Error Handling**

#### Reference Version:
- Simple error display in JSX
- No modals
- No global error handlers

#### Current Version:
- **Error Modal** (Dialog component)
- **Completion Modal** (Dialog component)
- **Global error handlers** for:
  - `window.addEventListener("error")`
  - `window.addEventListener("unhandledrejection")`
- Complex error message parsing

**Potential Issue**: The global error handlers might be interfering with the game loop or keyboard events.

---

### 4. **Additional Components**

#### Current Version Only:
- **ScanHUD** component - displays scan progress, game stats, extension info
- **Dialog** modals for errors and completion

---

### 5. **API Calls**

#### Reference Version:
- Only fetches extension icon
- No status checking

#### Current Version:
- Fetches extension icon
- Fetches extension name via `realScanService.getRealScanResults()`
- Checks scan status via `realScanService.checkScanStatus()`
- Multiple async operations that could cause race conditions

---

### 6. **Mobile Detection**

#### Current Version Only:
```javascript
const [isMobile, setIsMobile] = useState(false);

useEffect(() => {
  const checkMobile = () => {
    setIsMobile(window.innerWidth <= 768);
  };
  checkMobile();
  window.addEventListener("resize", checkMobile);
  return () => window.removeEventListener("resize", checkMobile);
}, []);
```

---

## Potential Issues in Current Version

### 1. **ResizeObserver Conflicts**
The current `ScanProgressPage` doesn't directly use ResizeObserver, but the `RocketGame` component does. However, the complex state management and multiple useEffect hooks might be causing re-renders that interfere with the game loop.

### 2. **Multiple State Updates**
With 10+ state variables, there are many potential re-renders that could reset the game state or interfere with keyboard event handling.

### 3. **Global Error Handlers**
The global error handlers might be catching and preventing keyboard events or game loop errors.

### 4. **Complex shouldShowGame Logic**
The multiple fallback conditions might cause the game to mount/unmount unexpectedly, resetting the rocket position.

---

## Recommendations

### To Fix Y-Axis Movement Issue:

1. **Simplify ScanProgressPage** - Remove unnecessary state and effects
2. **Remove Global Error Handlers** - They might be interfering with keyboard events
3. **Simplify shouldShowGame Logic** - Use the reference version's simple logic
4. **Remove ScanHUD if not critical** - It adds complexity and potential re-renders
5. **Remove Mobile Detection** - Not needed for basic functionality

### Minimal Working Version Should Have:
- Only essential state: `extensionLogo`, `scanComplete`, `userExited`
- Simple `shouldShowGame` logic from reference version
- No global error handlers
- No modals (or make them optional)
- No ScanHUD (or make it optional)
- No API status checking (rely on ScanContext)

---

## Files to Check

1. **ScanProgressPage.jsx** - Current version is 2.5x larger with many additions
2. **RocketGame.jsx** - Already fixed with ResizeObserver improvements
3. **ScanHUD.jsx** - Might be causing re-renders
4. **realScanService.js** - API calls might be causing issues

---

## Next Steps

1. Simplify `ScanProgressPage.jsx` to match reference version structure
2. Remove unnecessary state variables
3. Remove global error handlers (or make them optional)
4. Test Y-axis movement after simplification
5. Add features back one at a time to identify what breaks it


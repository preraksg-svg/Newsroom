Set objShell = CreateObject("WScript.Shell")
strDesktop = objShell.SpecialFolders("Desktop")
strTarget = "C:\Users\PIT\.gemini\antigravity\scratch\ZapwayNewsroom\Launch_Zapway_Newsroom.bat"

Set objShortcut = objShell.CreateShortcut(strDesktop & "\Zapway Newsroom.lnk")
objShortcut.TargetPath = strTarget
objShortcut.WorkingDirectory = "C:\Users\PIT\.gemini\antigravity\scratch\ZapwayNewsroom"
objShortcut.Description = "Launch Zapway EV Newsroom Server and Dashboard"
objShortcut.IconLocation = "shell32.dll,14" ' Icon index for a folder/globe style icon
objShortcut.Save

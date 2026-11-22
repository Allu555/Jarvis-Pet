Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
strApp = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
strScript = strDir & "\jarvis\spider_3d\app.py"
WshShell.CurrentDirectory = strDir & "\jarvis\spider_3d"
WshShell.Run """" & strApp & """ """ & strScript & """", 0, False

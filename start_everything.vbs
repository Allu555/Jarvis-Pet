Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
strApp = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Python\Python311\pythonw.exe"
If Not fso.FileExists(strApp) Then
    strApp = "pythonw.exe"
End If
strScript = strDir & "\main.py"
WshShell.CurrentDirectory = strDir
WshShell.Run """" & strApp & """ """ & strScript & """", 0, False


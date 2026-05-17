Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = appDir & "\.venv\Scripts\pythonw.exe"
entrypoint = appDir & "\launcher.pyw"
logPath = appDir & "\launcher.log"

If Not fso.FileExists(pythonw) Then
    MsgBox "Virtual environment not found: " & pythonw & vbCrLf & _
           "Reinstall pyStudyFlash or run install_env.ps1.", _
           16, "pyStudyFlash"
    WScript.Quit 1
End If

shell.CurrentDirectory = appDir
shell.Environment("PROCESS")("PYSTUDYFLASH_USE_APPDATA") = "1"

Set logFile = fso.OpenTextFile(logPath, 8, True)
logFile.WriteLine Now & " Starting pyStudyFlash"
logFile.WriteLine """" & pythonw & """ """ & entrypoint & """"
logFile.Close

' Do not use SW_HIDE here. It hides the first Qt window while the process stays alive.
shell.Run """" & pythonw & """ """ & entrypoint & """", 1, False

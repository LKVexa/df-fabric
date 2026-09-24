using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

internal static class Program
{
    private const string Version = "__VERSION__";
    private const string ExpectedPayloadSha256 = "__PAYLOAD_SHA__";

    [STAThread]
    private static int Main(string[] args)
    {
        string logPath = null;
        try
        {
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (String.IsNullOrWhiteSpace(local))
                throw new InvalidOperationException("LOCALAPPDATA is unavailable.");

            string logRoot = Path.Combine(local, "DF-VM-Technical-Institute", "logs");
            Directory.CreateDirectory(logRoot);
            logPath = Path.Combine(logRoot, "bootstrap-" + DateTime.Now.ToString("yyyyMMdd-HHmmss-fff") + ".log");
            Log(logPath, "Bootstrap v" + Version + " starting.");

            byte[] payload = DecodePayload();
            string actualHash = Sha256Hex(payload);
            Log(logPath, "Embedded payload SHA-256: " + actualHash);
            if (!String.Equals(actualHash, ExpectedPayloadSha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Embedded payload SHA-256 mismatch. Expected " + ExpectedPayloadSha256 + " but found " + actualHash + ".");

            string baseDir = Path.Combine(local, "DF-VM-Technical-Institute", Version);
            string installDir = Path.Combine(baseDir, "app");
            string marker = Path.Combine(baseDir, "payload.sha256");
            string[] required = new string[] {
                "index.html",
                Path.Combine("assets", "styles.css"),
                Path.Combine("assets", "data.js"),
                Path.Combine("assets", "site.js")
            };

            if (!CacheIsValid(installDir, marker, actualHash, required))
            {
                Log(logPath, "Cache missing or stale; extracting embedded institute.");
                string stagingParent = Path.Combine(local, "DF-VM-Technical-Institute", ".staging-" + Version + "-" + Process.GetCurrentProcess().Id.ToString());
                string stagingDir = Path.Combine(stagingParent, "app");
                SafeDeleteDirectory(stagingParent);
                Directory.CreateDirectory(stagingDir);
                ExtractZipSafely(payload, stagingDir);
                ValidateRequired(stagingDir, required);

                SafeDeleteDirectory(installDir);
                Directory.CreateDirectory(baseDir);
                Directory.Move(stagingDir, installDir);
                File.WriteAllText(marker, actualHash, Encoding.ASCII);
                SafeDeleteDirectory(stagingParent);
                Log(logPath, "Installed validated payload to " + installDir);
            }
            else
            {
                Log(logPath, "Validated cached payload at " + installDir);
            }

            string index = Path.Combine(installDir, "index.html");
            bool fullscreen = HasArg(args, "--fullscreen");
            LaunchInstitute(index, fullscreen, logPath);
            Log(logPath, "Launch request completed.");
            return 0;
        }
        catch (Exception ex)
        {
            try { if (!String.IsNullOrEmpty(logPath)) Log(logPath, "ERROR " + ex.ToString()); } catch { }
            string message = "DF VM Technical Institute could not start.\r\n\r\n" + ex.Message;
            if (!String.IsNullOrEmpty(logPath)) message += "\r\n\r\nDiagnostic log:\r\n" + logPath;
            MessageBox.Show(message, "DF VM Technical Institute - Launch Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static byte[] DecodePayload()
    {
        string base64 = String.Concat(new string[] {
__BASE64_CHUNKS__
        });
        return Convert.FromBase64String(base64);
    }

    private static bool CacheIsValid(string installDir, string marker, string expectedHash, string[] required)
    {
        if (!Directory.Exists(installDir) || !File.Exists(marker)) return false;
        string cached = File.ReadAllText(marker).Trim();
        if (!String.Equals(cached, expectedHash, StringComparison.OrdinalIgnoreCase)) return false;
        for (int i = 0; i < required.Length; i++)
            if (!File.Exists(Path.Combine(installDir, required[i]))) return false;
        return true;
    }

    private static void ValidateRequired(string root, string[] required)
    {
        for (int i = 0; i < required.Length; i++)
        {
            string p = Path.Combine(root, required[i]);
            if (!File.Exists(p)) throw new InvalidDataException("Payload validation failed; required file missing: " + required[i]);
        }
    }

    private static void ExtractZipSafely(byte[] payload, string destination)
    {
        string root = Path.GetFullPath(destination);
        if (!root.EndsWith(Path.DirectorySeparatorChar.ToString())) root += Path.DirectorySeparatorChar;

        using (MemoryStream ms = new MemoryStream(payload, false))
        using (ZipArchive archive = new ZipArchive(ms, ZipArchiveMode.Read, false))
        {
            foreach (ZipArchiveEntry entry in archive.Entries)
            {
                string outPath = Path.GetFullPath(Path.Combine(destination, entry.FullName.Replace('/', Path.DirectorySeparatorChar)));
                if (!outPath.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Blocked unsafe archive path: " + entry.FullName);

                if (String.IsNullOrEmpty(entry.Name))
                {
                    Directory.CreateDirectory(outPath);
                    continue;
                }

                string parent = Path.GetDirectoryName(outPath);
                if (!String.IsNullOrEmpty(parent)) Directory.CreateDirectory(parent);
                using (Stream input = entry.Open())
                using (FileStream output = new FileStream(outPath, FileMode.Create, FileAccess.Write, FileShare.None))
                    input.CopyTo(output);
            }
        }
    }

    private static void LaunchInstitute(string indexPath, bool fullscreen, string logPath)
    {
        Uri indexUri = new Uri(indexPath);
        string browser = FindBrowser();
        if (!String.IsNullOrEmpty(browser))
        {
            string args = "--app=\"" + indexUri.AbsoluteUri + "\" --no-first-run --no-default-browser-check --disable-extensions " + (fullscreen ? "--start-fullscreen" : "--start-maximized");
            Log(logPath, "Starting browser: " + browser + " " + args);
            ProcessStartInfo psi = new ProcessStartInfo(browser, args);
            psi.UseShellExecute = false;
            Process.Start(psi);
            return;
        }

        Log(logPath, "No Edge/Chrome installation found; using Windows default file association.");
        ProcessStartInfo fallback = new ProcessStartInfo(indexPath);
        fallback.UseShellExecute = true;
        Process.Start(fallback);
    }

    private static string FindBrowser()
    {
        List<string> candidates = new List<string>();
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), Path.Combine("Microsoft", "Edge", "Application", "msedge.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), Path.Combine("Microsoft", "Edge", "Application", "msedge.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Path.Combine("Microsoft", "Edge", "Application", "msedge.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), Path.Combine("Google", "Chrome", "Application", "chrome.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), Path.Combine("Google", "Chrome", "Application", "chrome.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Path.Combine("Google", "Chrome", "Application", "chrome.exe"));
        return candidates.Count > 0 ? candidates[0] : null;
    }

    private static void AddBrowserCandidate(List<string> list, string root, string relative)
    {
        if (String.IsNullOrWhiteSpace(root)) return;
        string p = Path.Combine(root, relative);
        if (File.Exists(p) && !list.Contains(p)) list.Add(p);
    }

    private static bool HasArg(string[] args, string expected)
    {
        if (args == null) return false;
        for (int i = 0; i < args.Length; i++)
            if (String.Equals(args[i], expected, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    private static string Sha256Hex(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
        {
            byte[] hash = sha.ComputeHash(bytes);
            StringBuilder sb = new StringBuilder(hash.Length * 2);
            for (int i = 0; i < hash.Length; i++) sb.Append(hash[i].ToString("x2"));
            return sb.ToString();
        }
    }

    private static void SafeDeleteDirectory(string path)
    {
        try { if (Directory.Exists(path)) Directory.Delete(path, true); } catch { }
    }

    private static void Log(string path, string message)
    {
        File.AppendAllText(path, DateTime.Now.ToString("o") + " " + message + Environment.NewLine, Encoding.UTF8);
    }
}

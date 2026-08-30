import React, {
  useEffect,
  useMemo,
  useState
} from "react";

import axios from "axios";

import ReactMarkdown from "react-markdown";

import {
  Upload,
  Search,
  Languages,
  FileText,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  ListChecks,
  CalendarDays,
  Users,
  Files,
  AlignLeft,
  BadgeCheck,
  GitCompareArrows,
  ArrowRight,
  X,
  Database,
  Save,
  Trash2,
  RefreshCw,
  FolderOpen,
  Library,
  Loader2,
  ExternalLink,
  Eye,
  BookOpen,
  BarChart3,
  Target,
  Trophy,
  Activity,
  LogIn,
  LogOut,
  UserPlus,
  UserCircle2,
  LockKeyhole,
  Mail,
  Moon,
  Sun
} from "lucide-react";


const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8001";


const TOKEN_KEY =
  "tn_insight_access_token";

const USER_KEY =
  "tn_insight_user";


const getStoredToken = () =>
  localStorage.getItem(
    TOKEN_KEY
  );


const authConfig = () => {

  const token =
    getStoredToken();

  if (!token) {
    return {};
  }

  return {
    headers: {
      Authorization:
        `Bearer ${token}`
    }
  };

};


const App = () => {

  const [
    darkMode,
    setDarkMode
  ] = useState(() => {

    const storedTheme =
      localStorage.getItem(
        "tn_insight_theme"
      );

    return storedTheme === "dark";

  });

  const [
    authMode,
    setAuthMode
  ] = useState("login");

  const [
    authName,
    setAuthName
  ] = useState("");

  const [
    authEmail,
    setAuthEmail
  ] = useState("");

  const [
    authPassword,
    setAuthPassword
  ] = useState("");

  const [
    authLoading,
    setAuthLoading
  ] = useState(false);

  const [
    authError,
    setAuthError
  ] = useState("");

  const [
    currentUser,
    setCurrentUser
  ] = useState(() => {

    try {

      const stored =
        localStorage.getItem(
          USER_KEY
        );

      return stored
        ? JSON.parse(
            stored
          )
        : null;

    } catch {

      return null;

    }

  });

  const [
    authChecking,
    setAuthChecking
  ] = useState(
    Boolean(
      getStoredToken()
    )
  );

  const [question, setQuestion] =
    useState("");

  const [
    backendStatus,
    setBackendStatus
  ] = useState("");


  const [
    selectedFile,
    setSelectedFile
  ] = useState(null);

  const [
    uploadResult,
    setUploadResult
  ] = useState(null);

  const [
    uploading,
    setUploading
  ] = useState(false);


  const [
    aiAnswer,
    setAiAnswer
  ] = useState("");

  const [
    sources,
    setSources
  ] = useState([]);

  const [
    searchResults,
    setSearchResults
  ] = useState([]);

  const [
    asking,
    setAsking
  ] = useState(false);


  const [
    language,
    setLanguage
  ] = useState("English");


  const [
    compareFileA,
    setCompareFileA
  ] = useState(null);

  const [
    compareFileB,
    setCompareFileB
  ] = useState(null);

  const [
    comparing,
    setComparing
  ] = useState(false);

  const [
    comparisonResult,
    setComparisonResult
  ] = useState(null);


  const [
    libraryDocuments,
    setLibraryDocuments
  ] = useState([]);

  const [
    libraryLoading,
    setLibraryLoading
  ] = useState(false);

  const [
    librarySearch,
    setLibrarySearch
  ] = useState("");

  const [
    departmentFilter,
    setDepartmentFilter
  ] = useState("All");

  const [
    typeFilter,
    setTypeFilter
  ] = useState("All");

  const [
    yearFilter,
    setYearFilter
  ] = useState("All");


  const [
    saveTitle,
    setSaveTitle
  ] = useState("");

  const [
    saveDepartment,
    setSaveDepartment
  ] = useState("");

  const [
    saveDocumentType,
    setSaveDocumentType
  ] = useState(
    "Government Order"
  );

  const [
    saveYear,
    setSaveYear
  ] = useState("");

  const [
    savingDocument,
    setSavingDocument
  ] = useState(false);

  const [
    loadingDocumentId,
    setLoadingDocumentId
  ] = useState(null);

  const [
    deletingDocumentId,
    setDeletingDocumentId
  ] = useState(null);


  const [
    pdfViewer,
    setPdfViewer
  ] = useState({
    open: false,
    title: "",
    url: "",
    page: 1,
    blobUrl: ""
  });


  const [
    evaluationResult,
    setEvaluationResult
  ] = useState(null);

  const [
    evaluationLoading,
    setEvaluationLoading
  ] = useState(false);

  const [
    evaluationDataset,
    setEvaluationDataset
  ] = useState(null);


  const quickActions = [

    {
      title: "Summarize",
      icon:
        <AlignLeft size={17} />,
      english:
        "Summarize the important points in this document. Include the purpose, major provisions, important conditions and relevant page citations.",
      tamil:
        "இந்த ஆவணத்தின் முக்கிய அம்சங்களை எளிய தமிழில் சுருக்கமாக விளக்கவும். தொடர்புடைய பக்க எண்களையும் குறிப்பிடவும்."
    },

    {
      title: "Eligibility",
      icon:
        <BadgeCheck size={17} />,
      english:
        "Extract all eligibility conditions mentioned in this document. Include relevant page citations.",
      tamil:
        "இந்த ஆவணத்தில் குறிப்பிடப்பட்டுள்ள அனைத்து தகுதி நிபந்தனைகளையும் பக்க எண்களுடன் பட்டியலிடவும்."
    },

    {
      title: "Deadlines",
      icon:
        <CalendarDays size={17} />,
      english:
        "Extract all important dates, deadlines and time limits from this document. Include page citations.",
      tamil:
        "இந்த ஆவணத்தில் உள்ள முக்கிய தேதிகள் மற்றும் காலவரம்புகளை பக்க எண்களுடன் குறிப்பிடவும்."
    },

    {
      title:
        "Required Documents",
      icon:
        <Files size={17} />,
      english:
        "List all documents, certificates, forms or proofs required according to this document. Include page citations.",
      tamil:
        "தேவையான ஆவணங்கள் மற்றும் சான்றிதழ்களை பக்க எண்களுடன் பட்டியலிடவும்."
    },

    {
      title:
        "Who is Affected?",
      icon:
        <Users size={17} />,
      english:
        "Identify who is affected by this document and include page citations.",
      tamil:
        "இந்த ஆவணம் யாருக்கு பொருந்துகிறது என்பதை பக்க எண்களுடன் விளக்கவும்."
    },

    {
      title:
        "Explain Simply",
      icon:
        <ListChecks size={17} />,
      english:
        "Explain this government document in very simple English for an ordinary citizen. Include page citations.",
      tamil:
        "இந்த அரசாங்க ஆவணத்தை பொதுமக்கள் புரியும் எளிய தமிழில் பக்க எண்களுடன் விளக்கவும்."
    }

  ];


  useEffect(() => {

    restoreSession();

  }, []);


  useEffect(() => {

    localStorage.setItem(
      "tn_insight_theme",
      darkMode
        ? "dark"
        : "light"
    );

  }, [darkMode]);


  useEffect(() => {

    if (currentUser) {

      fetchLibrary();

    }

  }, [currentUser]);


  const clearLocalSession =
    () => {

      localStorage.removeItem(
        TOKEN_KEY
      );

      localStorage.removeItem(
        USER_KEY
      );

      setCurrentUser(
        null
      );

      setLibraryDocuments(
        []
      );

      setUploadResult(
        null
      );

      setSelectedFile(
        null
      );

      setEvaluationResult(
        null
      );

      setEvaluationDataset(
        null
      );

      resetQuestionResults();

    };


  const restoreSession =
    async () => {

      const token =
        getStoredToken();

      if (!token) {

        setAuthChecking(
          false
        );

        return;
      }

      try {

        const { data } =
          await axios.get(
            `${API_BASE}/auth/me`,
            authConfig()
          );

        if (
          data.success
          && data.user
        ) {

          localStorage.setItem(
            USER_KEY,
            JSON.stringify(
              data.user
            )
          );

          setCurrentUser(
            data.user
          );

        } else {

          clearLocalSession();

        }

      } catch (error) {

        console.error(
          "Session restore failed:",
          error
        );

        clearLocalSession();

      } finally {

        setAuthChecking(
          false
        );

      }

    };


  const submitAuth =
    async () => {

      const email =
        authEmail.trim();

      const password =
        authPassword;

      if (!email) {

        setAuthError(
          "Enter your email address"
        );

        return;
      }

      if (!password) {

        setAuthError(
          "Enter your password"
        );

        return;
      }

      if (
        authMode === "register"
        && !authName.trim()
      ) {

        setAuthError(
          "Enter your name"
        );

        return;
      }

      try {

        setAuthLoading(
          true
        );

        setAuthError(
          ""
        );

        const endpoint =
          authMode === "register"
            ? "/auth/register"
            : "/auth/login";

        const payload =
          authMode === "register"
            ? {
                name:
                  authName.trim(),
                email,
                password
              }
            : {
                email,
                password
              };

        const { data } =
          await axios.post(
            `${API_BASE}${endpoint}`,
            payload
          );

        if (
          !data.success
          || !data.access_token
          || !data.user
        ) {

          setAuthError(
            data.message
            || "Authentication failed"
          );

          return;
        }

        localStorage.setItem(
          TOKEN_KEY,
          data.access_token
        );

        localStorage.setItem(
          USER_KEY,
          JSON.stringify(
            data.user
          )
        );

        setCurrentUser(
          data.user
        );

        setAuthPassword(
          ""
        );

      } catch (error) {

        console.error(
          "Authentication error:",
          error
        );

        setAuthError(
          error?.response?.data?.detail
          || "Unable to connect to authentication service"
        );

      } finally {

        setAuthLoading(
          false
        );

      }

    };


  const logoutUser =
    async () => {

      try {

        await axios.post(
          `${API_BASE}/auth/logout`,
          {},
          authConfig()
        );

      } catch (error) {

        console.error(
          "Logout error:",
          error
        );

      } finally {

        clearLocalSession();

      }

    };


  const fetchLibrary =
    async () => {

      try {

        setLibraryLoading(true);

        const { data } =
          await axios.get(
            `${API_BASE}/library`,
            authConfig()
          );


        if (data.success) {

          setLibraryDocuments(
            data.documents || []
          );

        }


      } catch (error) {

        console.error(error);

      } finally {

        setLibraryLoading(false);

      }

    };


  const resetQuestionResults =
    () => {

      setQuestion("");
      setAiAnswer("");
      setSources([]);
      setSearchResults([]);

    };


  const testBackend =
    async () => {

      try {

        const { data } =
          await axios.get(
            `${API_BASE}/`
          );

        setBackendStatus(
          data.message
        );

      } catch {

        setBackendStatus(
          "Backend connection failed"
        );

      }

    };


  const uploadPdf =
    async () => {

      if (!selectedFile) {

        alert(
          "Please select a PDF"
        );

        return;
      }


      try {

        setUploading(true);

        resetQuestionResults();

        setUploadResult(null);


        const formData =
          new FormData();


        formData.append(
          "file",
          selectedFile
        );


        const { data } =
          await axios.post(
            `${API_BASE}/upload-pdf`,
            formData,
            authConfig()
          );


        if (!data.success) {

          alert(
            data.message ||
            "PDF processing failed"
          );

          return;
        }


        setUploadResult(
          data
        );


        setSaveTitle(
          selectedFile.name.replace(
            /\.pdf$/i,
            ""
          )
        );


      } catch (error) {

        console.error(error);

        alert(
          "PDF upload failed"
        );

      } finally {

        setUploading(false);

      }

    };


  const saveCurrentDocument =
    async () => {

      if (!saveTitle.trim()) {

        alert(
          "Enter document title"
        );

        return;
      }


      try {

        setSavingDocument(true);


        const { data } =
          await axios.post(
            `${API_BASE}/save-current-document`,
            {
              title:
                saveTitle,

              department:
                saveDepartment
                || "Unknown",

              document_type:
                saveDocumentType,

              year:
                saveYear
                || "Unknown"
            },
            authConfig()
          );


        if (!data.success) {

          alert(
            data.message
          );

          return;
        }


        alert(
          data.message
        );


        if (data.document) {

          setUploadResult(
            previous => ({
              ...previous,
              document_id:
                data.document.id,
              pdf_available:
                data.document
                  .pdf_available
            })
          );

        }


        await fetchLibrary();


      } catch (error) {

        console.error(error);

        alert(
          "Unable to save document"
        );

      } finally {

        setSavingDocument(false);

      }

    };


  const loadLibraryDocument =
    async document => {

      try {

        setLoadingDocumentId(
          document.id
        );


        const { data } =
          await axios.post(
            `${API_BASE}/load-library-document/${document.id}`,
            {},
            authConfig()
          );


        if (!data.success) {

          alert(
            data.message
          );

          return;
        }


        const loaded =
          data.document;


        setSelectedFile(null);


        setUploadResult({
          success: true,

          filename:
            loaded.filename,

          title:
            loaded.title,

          total_pages:
            loaded.total_pages,

          total_chunks:
            loaded.total_chunks,

          retrieval_method:
            "TF-IDF + BM25 Hybrid Search",

          loaded_from_library:
            true,

          document_id:
            loaded.id,

          pdf_available:
            loaded.pdf_available
        });


        resetQuestionResults();


        window.scrollTo({
          top: 0,
          behavior: "smooth"
        });


      } catch (error) {

        console.error(error);

        alert(
          "Unable to load document"
        );

      } finally {

        setLoadingDocumentId(
          null
        );

      }

    };


  const deleteLibraryDocument =
    async document => {

      if (
        !window.confirm(
          `Delete "${document.title}"?`
        )
      ) {
        return;
      }


      try {

        setDeletingDocumentId(
          document.id
        );


        const { data } =
          await axios.delete(
            `${API_BASE}/library/${document.id}`,
            authConfig()
          );


        if (!data.success) {

          alert(
            data.message
          );

          return;
        }


        await fetchLibrary();


      } catch {

        alert(
          "Unable to delete document"
        );

      } finally {

        setDeletingDocumentId(
          null
        );

      }

    };


  const askQuestion =
    async (
      customQuestion = null
    ) => {

      const finalQuestion =
        customQuestion
        || question;


      if (!finalQuestion.trim()) {

        alert(
          "Enter a question"
        );

        return;
      }


      if (!uploadResult?.success) {

        alert(
          "Load a document first"
        );

        return;
      }


      try {

        setAsking(true);

        setAiAnswer("");
        setSources([]);
        setSearchResults([]);


        if (customQuestion) {

          setQuestion(
            customQuestion
          );

        }


        const { data } =
          await axios.post(
            `${API_BASE}/ask`,
            {
              question:
                finalQuestion,

              language
            },
            authConfig()
          );


        if (!data.success) {

          alert(
            data.message
          );

          return;
        }


        setAiAnswer(
          data.answer || ""
        );

        setSources(
          data.sources || []
        );

        setSearchResults(
          data.results || []
        );


      } catch (error) {

        console.error(error);

        alert(
          "Question failed"
        );

      } finally {

        setAsking(false);

      }

    };


  const runQuickAction =
    action => {

      askQuestion(
        language === "Tamil"
          ? action.tamil
          : action.english
      );

    };


  const compareDocuments =
    async () => {

      if (
        !compareFileA
        || !compareFileB
      ) {

        alert(
          "Select both PDFs"
        );

        return;
      }


      try {

        setComparing(true);

        setComparisonResult(null);


        const formData =
          new FormData();


        formData.append(
          "file_a",
          compareFileA
        );

        formData.append(
          "file_b",
          compareFileB
        );

        formData.append(
          "language",
          language
        );


        const token =
          getStoredToken();

        if (!token) {

          alert(
            "Your session has expired. Please login again."
          );

          clearLocalSession();

          return;
        }


        const { data } =
          await axios.post(
            `${API_BASE}/compare-documents`,
            formData,
            {
              headers: {
                Authorization:
                  `Bearer ${token}`
              }
            }
          );


        if (!data.success) {

          alert(
            data.message
          );

          return;
        }


        setComparisonResult(
          data
        );


      } catch (error) {

        console.error(
          "Document comparison error:",
          error
        );

        if (
          error?.response?.status
          === 401
        ) {

          alert(
            "Your login session is invalid or expired. Please login again."
          );

          clearLocalSession();

          return;
        }

        alert(
          error?.response?.data?.detail
          || error?.response?.data?.message
          || "Document comparison failed"
        );

      } finally {

        setComparing(false);

      }

    };


  const openViewer =
    async (
      url,
      page,
      title
    ) => {

      try {

        const response =
          await axios.get(
            url,
            {
              ...authConfig(),
              responseType:
                "blob"
            }
          );

        const blobUrl =
          URL.createObjectURL(
            response.data
          );

        setPdfViewer(
          previous => {

            if (
              previous.blobUrl
            ) {

              URL.revokeObjectURL(
                previous.blobUrl
              );

            }

            return {
              open: true,
              url,
              blobUrl,
              page:
                Number(page) || 1,
              title:
                title || "Source PDF"
            };

          }
        );

      } catch (error) {

        console.error(
          "PDF viewer error:",
          error
        );

        alert(
          "Unable to open the PDF"
        );

      }

    };


  const openCurrentSource =
    page => {

      if (
        uploadResult
          ?.loaded_from_library
      ) {

        if (
          !uploadResult
            .pdf_available
        ) {

          alert(
            "The original PDF was not stored for this older library entry. Re-upload and save the PDF once to enable clickable pages."
          );

          return;
        }


        openViewer(
          `${API_BASE}/library/${uploadResult.document_id}/pdf`,
          page,
          uploadResult.filename
        );

        return;

      }


      openViewer(
        `${API_BASE}/current-pdf`,
        page,
        uploadResult?.filename
      );

    };


  const openComparisonSource =
    (
      side,
      page
    ) => {

      const isA =
        side === "a";


      openViewer(
        `${API_BASE}/comparison/${side}/pdf`,
        page,
        isA
          ? comparisonResult
              ?.document_a
              ?.filename
          : comparisonResult
              ?.document_b
              ?.filename
      );

    };


  const fetchEvaluationDataset =
    async () => {

      try {

        const { data } =
          await axios.get(
            `${API_BASE}/evaluation/dataset`,
            authConfig()
          );

        if (data.success) {

          setEvaluationDataset(
            data
          );

        }

      } catch (error) {

        console.error(
          "Evaluation dataset error:",
          error
        );

      }

    };


  const runDatasetEvaluation =
    async () => {

      try {

        setEvaluationLoading(
          true
        );

        setEvaluationResult(
          null
        );

        const { data } =
          await axios.post(
            `${API_BASE}/evaluation/run-dataset`,
            {},
            authConfig()
          );

        if (!data.success) {

          alert(
            data.message ||
            "Evaluation failed"
          );

          return;
        }

        setEvaluationResult(
          data
        );

      } catch (error) {

        console.error(
          "Evaluation error:",
          error
        );

        alert(
          "Evaluation failed"
        );

      } finally {

        setEvaluationLoading(
          false
        );

      }

    };


  const departments =
    useMemo(
      () => [
        "All",
        ...new Set(
          libraryDocuments
            .map(
              d => d.department
            )
            .filter(Boolean)
        )
      ],
      [libraryDocuments]
    );


  const documentTypes =
    useMemo(
      () => [
        "All",
        ...new Set(
          libraryDocuments
            .map(
              d =>
                d.document_type
            )
            .filter(Boolean)
        )
      ],
      [libraryDocuments]
    );


  const years =
    useMemo(
      () => [
        "All",
        ...new Set(
          libraryDocuments
            .map(
              d => d.year
            )
            .filter(Boolean)
        )
      ],
      [libraryDocuments]
    );


  const filteredLibrary =
    useMemo(
      () => {

        const query =
          librarySearch
            .toLowerCase()
            .trim();


        return libraryDocuments
          .filter(
            document => {

              const searchable = [
                document.title,
                document.filename,
                document.department,
                document.document_type,
                document.year
              ]
                .join(" ")
                .toLowerCase();


              return (
                (
                  !query
                  || searchable.includes(
                    query
                  )
                )
                &&
                (
                  departmentFilter
                  === "All"
                  ||
                  document.department
                  === departmentFilter
                )
                &&
                (
                  typeFilter
                  === "All"
                  ||
                  document.document_type
                  === typeFilter
                )
                &&
                (
                  yearFilter
                  === "All"
                  ||
                  document.year
                  === yearFilter
                )
              );

            }
          );

      },
      [
        libraryDocuments,
        librarySearch,
        departmentFilter,
        typeFilter,
        yearFilter
      ]
    );


  if (authChecking) {

    return (

      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-indigo-950 to-violet-950">

        <div className="text-center text-white">

          <div className="w-16 h-16 rounded-3xl bg-white/10 border border-white/15 backdrop-blur-xl mx-auto flex items-center justify-center shadow-2xl">

            <Loader2
              size={28}
              className="animate-spin"
            />

          </div>

          <p className="mt-4 text-sm text-white/70">

            Restoring your secure session...

          </p>

        </div>

      </div>

    );

  }


  if (!currentUser) {

    return (

      <AuthScreen
        mode={authMode}
        setMode={setAuthMode}
        name={authName}
        setName={setAuthName}
        email={authEmail}
        setEmail={setAuthEmail}
        password={authPassword}
        setPassword={setAuthPassword}
        loading={authLoading}
        error={authError}
        onSubmit={submitAuth}
      />

    );

  }


  return (

    <div className={`${darkMode ? "tn-dark" : ""} min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/70 text-slate-900 text-[15px] sm:text-base antialiased selection:bg-indigo-200/70 selection:text-indigo-950 transition-colors duration-500`}>


      <style>{`
        .tn-dark {
          background:
            radial-gradient(circle at 8% 8%, rgba(79,70,229,0.18), transparent 26%),
            radial-gradient(circle at 92% 35%, rgba(124,58,237,0.13), transparent 28%),
            linear-gradient(135deg, #070b14 0%, #0b1120 48%, #111827 100%) !important;
          color: #e5e7eb !important;
          color-scheme: dark;
        }

        .tn-dark header {
          background: rgba(8, 13, 24, 0.82) !important;
          border-color: rgba(71, 85, 105, 0.42) !important;
        }

        .tn-dark footer {
          background: rgba(8, 13, 24, 0.76) !important;
          border-color: rgba(71, 85, 105, 0.42) !important;
        }

        .tn-dark .bg-white,
        .tn-dark .bg-white\\/80,
        .tn-dark .bg-white\\/85,
        .tn-dark .bg-white\\/90,
        .tn-dark .bg-white\\/95,
        .tn-dark .bg-white\\/70,
        .tn-dark .bg-white\\/75 {
          background-color: rgba(15, 23, 42, 0.88) !important;
        }

        .tn-dark .from-white {
          --tw-gradient-from: rgba(15, 23, 42, 0.96) var(--tw-gradient-from-position) !important;
          --tw-gradient-to: rgba(15, 23, 42, 0) var(--tw-gradient-to-position) !important;
        }

        .tn-dark .via-white {
          --tw-gradient-to: rgba(15, 23, 42, 0) var(--tw-gradient-to-position) !important;
          --tw-gradient-stops: var(--tw-gradient-from), rgba(17, 24, 39, 0.96) var(--tw-gradient-via-position), var(--tw-gradient-to) !important;
        }

        .tn-dark .to-indigo-50\\/70,
        .tn-dark .to-indigo-50\\/60,
        .tn-dark .to-indigo-50\\/40,
        .tn-dark .to-violet-50,
        .tn-dark .to-fuchsia-50\\/50 {
          --tw-gradient-to: rgba(49, 46, 129, 0.18) var(--tw-gradient-to-position) !important;
        }

        .tn-dark .bg-slate-50,
        .tn-dark .bg-slate-50\\/60,
        .tn-dark .bg-slate-50\\/90,
        .tn-dark .bg-slate-100 {
          background-color: rgba(30, 41, 59, 0.86) !important;
        }

        .tn-dark .bg-indigo-50,
        .tn-dark .bg-indigo-50\\/60,
        .tn-dark .bg-indigo-50\\/90 {
          background-color: rgba(49, 46, 129, 0.22) !important;
        }

        .tn-dark .bg-emerald-50,
        .tn-dark .bg-emerald-50\\/90 {
          background-color: rgba(6, 78, 59, 0.22) !important;
        }

        .tn-dark .text-slate-900,
        .tn-dark .text-slate-800 {
          color: #f8fafc !important;
        }

        .tn-dark .text-slate-700 {
          color: #e2e8f0 !important;
        }

        .tn-dark .text-slate-600 {
          color: #cbd5e1 !important;
        }

        .tn-dark .text-slate-500,
        .tn-dark .text-slate-400 {
          color: #94a3b8 !important;
        }

        .tn-dark .border-slate-200,
        .tn-dark .border-slate-200\\/80,
        .tn-dark .border-white\\/70,
        .tn-dark .border-white\\/80,
        .tn-dark .border-white\\/90 {
          border-color: rgba(100, 116, 139, 0.34) !important;
        }

        .tn-dark input,
        .tn-dark textarea,
        .tn-dark select {
          background: rgba(15, 23, 42, 0.94) !important;
          color: #f8fafc !important;
          border-color: rgba(100, 116, 139, 0.48) !important;
        }

        .tn-dark input::placeholder,
        .tn-dark textarea::placeholder {
          color: #64748b !important;
        }

        .tn-dark .theme-toggle {
          background: rgba(30, 41, 59, 0.92) !important;
          color: #f8fafc !important;
          border-color: rgba(99, 102, 241, 0.40) !important;
        }

        .tn-dark .theme-toggle:hover {
          background: rgba(49, 46, 129, 0.72) !important;
          color: white !important;
        }

        .tn-dark button:not(:disabled),
        .tn-dark a {
          transition:
            transform 220ms ease,
            box-shadow 220ms ease,
            background-color 220ms ease,
            border-color 220ms ease,
            color 220ms ease;
        }

        .tn-dark iframe {
          background: #0f172a;
        }

        /* Strong dark-mode treatment for light gradient cards such as AI Comparison */
        .tn-dark .from-indigo-50,
        .tn-dark .from-indigo-50\/60,
        .tn-dark .from-indigo-50\/70,
        .tn-dark .from-indigo-50\/90,
        .tn-dark .from-violet-50,
        .tn-dark .from-fuchsia-50 {
          --tw-gradient-from: rgba(15, 23, 42, 0.98) var(--tw-gradient-from-position) !important;
          --tw-gradient-to: rgba(15, 23, 42, 0) var(--tw-gradient-to-position) !important;
        }

        .tn-dark .via-indigo-50,
        .tn-dark .via-violet-50,
        .tn-dark .via-violet-50\/70,
        .tn-dark .via-fuchsia-50,
        .tn-dark .via-white {
          --tw-gradient-to: rgba(17, 24, 39, 0) var(--tw-gradient-to-position) !important;
          --tw-gradient-stops:
            var(--tw-gradient-from),
            rgba(30, 41, 59, 0.96) var(--tw-gradient-via-position),
            var(--tw-gradient-to) !important;
        }

        .tn-dark .to-indigo-50,
        .tn-dark .to-indigo-50\/40,
        .tn-dark .to-indigo-50\/60,
        .tn-dark .to-indigo-50\/70,
        .tn-dark .to-violet-50,
        .tn-dark .to-violet-50\/70,
        .tn-dark .to-fuchsia-50,
        .tn-dark .to-fuchsia-50\/50 {
          --tw-gradient-to: rgba(49, 46, 129, 0.28) var(--tw-gradient-to-position) !important;
        }

        .tn-dark .text-indigo-600,
        .tn-dark .text-indigo-700 {
          color: #c7d2fe !important;
        }

        .tn-dark .text-emerald-700 {
          color: #6ee7b7 !important;
        }

        .tn-dark strong,
        .tn-dark b,
        .tn-dark h1,
        .tn-dark h2,
        .tn-dark h3,
        .tn-dark h4,
        .tn-dark h5,
        .tn-dark h6 {
          color: #f8fafc !important;
        }

        .tn-dark ul,
        .tn-dark ol,
        .tn-dark li {
          color: #e2e8f0 !important;
        }

        .tn-dark blockquote {
          background: rgba(49, 46, 129, 0.24) !important;
          color: #e2e8f0 !important;
          border-color: rgba(165, 180, 252, 0.55) !important;
        }

        .tn-dark code {
          background: rgba(30, 41, 59, 0.96) !important;
          color: #c7d2fe !important;
        }

        .tn-dark .tn-markdown,
        .tn-dark .tn-markdown p,
        .tn-dark .tn-markdown li {
          color: #e5e7eb !important;
        }

        .tn-dark .tn-markdown h1,
        .tn-dark .tn-markdown h2,
        .tn-dark .tn-markdown h3,
        .tn-dark .tn-markdown h4,
        .tn-dark .tn-markdown strong {
          color: #ffffff !important;
        }
      `}</style>

      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full bg-indigo-300/20 blur-3xl" />
        <div className="absolute top-1/3 -right-32 h-96 w-96 rounded-full bg-violet-300/20 blur-3xl" />
        <div className="absolute bottom-0 left-1/4 h-80 w-80 rounded-full bg-cyan-200/20 blur-3xl" />
      </div>


      <header className="sticky top-0 z-40 border-b border-white/70 bg-white/80 backdrop-blur-xl shadow-[0_8px_30px_rgba(15,23,42,0.05)]">

        <div className="max-w-7xl mx-auto px-5 sm:px-6 py-3.5 flex justify-between items-center">


          <div className="flex gap-3 items-center">

            <div className="w-11 h-11 bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-500 rounded-2xl text-white flex items-center justify-center shadow-lg shadow-indigo-500/25 ring-1 ring-white/60">

              <Sparkles size={21} />

            </div>


            <div>

              <h1 className="font-bold text-xl">

                TN Insight AI

              </h1>

              <p className="text-sm text-slate-500 font-medium">

                Government Document Intelligence

              </p>

            </div>

          </div>


          <div className="flex items-center gap-3">

            <nav className="hidden md:flex items-center gap-1.5 text-sm font-medium text-slate-600 bg-slate-100/70 border border-slate-200/70 rounded-2xl p-1.5">

              <a href="#library" className="px-3.5 py-2 rounded-xl transition-all duration-300 hover:bg-white hover:text-indigo-700 hover:shadow-md hover:-translate-y-0.5">
                Library
              </a>

              <a href="#compare" className="px-3.5 py-2 rounded-xl transition-all duration-300 hover:bg-white hover:text-indigo-700 hover:shadow-md hover:-translate-y-0.5">
                Compare
              </a>

              <a href="#features" className="px-3.5 py-2 rounded-xl transition-all duration-300 hover:bg-white hover:text-indigo-700 hover:shadow-md hover:-translate-y-0.5">
                Features
              </a>

            </nav>

            <button
              onClick={() =>
                setDarkMode(
                  previous =>
                    !previous
                )
              }
              className="theme-toggle inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white/90 text-slate-700 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-indigo-300 hover:text-indigo-700 hover:shadow-lg hover:shadow-indigo-500/10 active:translate-y-0"
              title={
                darkMode
                  ? "Switch to light mode"
                  : "Switch to dark mode"
              }
              aria-label={
                darkMode
                  ? "Switch to light mode"
                  : "Switch to dark mode"
              }
            >

              {darkMode ? (
                <Sun size={18} />
              ) : (
                <Moon size={18} />
              )}

            </button>


            {currentUser && (

              <div className="hidden sm:flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 px-3 py-2 shadow-sm">

                <UserCircle2
                  size={18}
                  className="text-indigo-600"
                />

                <div className="leading-tight">

                  <p className="text-xs font-semibold text-slate-800 max-w-[120px] truncate">

                    {currentUser.name}

                  </p>

                  <p className="text-[10px] text-slate-400 max-w-[140px] truncate">

                    {currentUser.email}

                  </p>

                </div>

              </div>

            )}

            {currentUser && (

              <button
                onClick={logoutUser}
                className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-3.5 py-2.5 text-sm font-semibold text-white shadow-md transition-all duration-300 hover:-translate-y-0.5 hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-500/20 active:translate-y-0"
              >

                <LogOut size={16} />

                <span className="hidden lg:inline">
                  Logout
                </span>

              </button>

            )}

          </div>


        </div>

      </header>


      <main className="relative z-10">


        <section className="relative max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-8 pt-12 pb-16 sm:pt-16 sm:pb-20">


          <div className="relative overflow-hidden grid lg:grid-cols-2 gap-8 xl:gap-12 items-start rounded-[34px] border border-white/90 bg-white/75 backdrop-blur-xl p-6 sm:p-9 lg:p-10 shadow-[0_30px_90px_-35px_rgba(79,70,229,0.34)] transition-all duration-500 hover:shadow-[0_38px_110px_-35px_rgba(79,70,229,0.42)]">


            <div>


              <div className="inline-flex items-center gap-2 px-3.5 py-2 bg-indigo-50/90 text-indigo-700 border border-indigo-100 rounded-full text-sm font-medium shadow-sm">

                <ShieldCheck size={16} />

                AI-powered Tamil Nadu document analysis

              </div>


              <h2 className="text-4xl sm:text-5xl xl:text-6xl font-black tracking-tight mt-6 leading-[1.05]">

                Understand Government Documents

                <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-500 bg-clip-text text-transparent">

                  {" "}with AI

                </span>

              </h2>


              <p className="text-slate-600 mt-6 text-lg sm:text-xl leading-8 sm:leading-9 max-w-xl font-medium">

                Search, simplify, compare and verify Government Orders,
                circulars and notifications with citation-grounded AI.

              </p>


              <div className="flex flex-wrap gap-3 mt-6">


                <label className="group bg-gradient-to-r from-indigo-600 to-violet-600 text-white px-5 py-3.5 rounded-2xl flex items-center gap-2 cursor-pointer shadow-lg shadow-indigo-500/20 hover:shadow-xl hover:-translate-y-0.5 transition-all">

                  <Upload size={18} />

                  Select PDF


                  <input
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={
                      event => {

                        const file =
                          event.target
                            .files[0];

                        setSelectedFile(
                          file || null
                        );

                        setUploadResult(
                          null
                        );

                        resetQuestionResults();

                      }
                    }
                  />

                </label>


                <a
                  href="#library"
                  className="px-5 py-3.5 bg-white/90 border border-slate-200 rounded-2xl flex items-center gap-2 shadow-sm hover:border-indigo-200 hover:text-indigo-700 hover:-translate-y-0.5 transition-all"
                >

                  <Library size={18} />

                  Library

                </a>


                <a
                  href="#compare"
                  className="px-5 py-3.5 bg-white/90 border border-slate-200 rounded-2xl flex items-center gap-2 shadow-sm hover:border-indigo-200 hover:text-indigo-700 hover:-translate-y-0.5 transition-all"
                >

                  <GitCompareArrows
                    size={18}
                  />

                  Compare

                </a>


              </div>


              {selectedFile && (

                <div className="bg-white/90 border border-slate-200/80 rounded-3xl p-5 mt-5 shadow-xl shadow-slate-900/5">


                  <div className="flex items-center gap-3">

                    <FileText
                      className="text-indigo-600"
                    />

                    <div>

                      <p className="font-medium">

                        {selectedFile.name}

                      </p>

                      <p className="text-xs text-slate-400">

                        {(
                          selectedFile.size
                          / 1024
                          / 1024
                        ).toFixed(2)} MB

                      </p>

                    </div>

                  </div>


                  <button
                    onClick={uploadPdf}
                    disabled={uploading}
                    className="mt-4 w-full bg-slate-950 text-white py-3.5 rounded-2xl flex justify-center gap-2 shadow-lg shadow-slate-900/15 hover:bg-indigo-700 hover:-translate-y-0.5 transition-all disabled:opacity-60"
                  >

                    {uploading ? (
                      <>
                        <Loader2
                          size={18}
                          className="animate-spin"
                        />
                        Processing...
                      </>
                    ) : (
                      "Process Document"
                    )}

                  </button>


                </div>

              )}


              {uploadResult?.success && (

                <div className="mt-5 bg-gradient-to-br from-emerald-50 to-teal-50/70 border border-emerald-200/80 rounded-3xl p-5 shadow-lg shadow-emerald-900/5">


                  <div className="flex gap-2 items-center text-emerald-700">

                    <CheckCircle2
                      size={19}
                    />

                    <strong>

                      {
                        uploadResult
                          .loaded_from_library
                          ? "Loaded from library"
                          : "Document processed"
                      }

                    </strong>

                  </div>


                  <div className="grid sm:grid-cols-2 gap-3 mt-4">

                    <InfoCard
                      title="File"
                      value={
                        uploadResult.filename
                      }
                    />

                    <InfoCard
                      title="Pages"
                      value={
                        uploadResult.total_pages
                      }
                    />

                    <InfoCard
                      title="Chunks"
                      value={
                        uploadResult.total_chunks
                      }
                    />

                    <InfoCard
                      title="Retrieval"
                      value={
                        uploadResult.retrieval_method
                      }
                    />

                  </div>


                  {uploadResult
                    .pdf_available !== false && (

                    <button
                      onClick={() =>
                        openCurrentSource(
                          1
                        )
                      }
                      className="mt-4 border border-emerald-200 bg-white/90 text-emerald-700 px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"
                    >

                      <BookOpen
                        size={17}
                      />

                      View Original PDF

                    </button>

                  )}


                  {!uploadResult
                    .loaded_from_library && (

                    <div className="border-t border-emerald-200 mt-5 pt-5">


                      <div className="flex gap-2 items-center font-semibold">

                        <Save size={18} />

                        Save to Library

                      </div>


                      <div className="grid sm:grid-cols-2 gap-3 mt-4">

                        <Input
                          value={saveTitle}
                          setValue={
                            setSaveTitle
                          }
                          placeholder="Title"
                        />

                        <Input
                          value={
                            saveDepartment
                          }
                          setValue={
                            setSaveDepartment
                          }
                          placeholder="Department"
                        />


                        <select
                          value={
                            saveDocumentType
                          }
                          onChange={
                            event =>
                              setSaveDocumentType(
                                event.target.value
                              )
                          }
                          className="border border-slate-200 rounded-2xl px-3.5 py-3 bg-white/90 outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition"
                        >

                          <option>
                            Government Order
                          </option>

                          <option>
                            Gazette Notification
                          </option>

                          <option>
                            Circular
                          </option>

                          <option>
                            Notification
                          </option>

                          <option>
                            Policy Document
                          </option>

                        </select>


                        <Input
                          value={saveYear}
                          setValue={
                            setSaveYear
                          }
                          placeholder="Year"
                        />

                      </div>


                      <button
                        onClick={
                          saveCurrentDocument
                        }
                        disabled={
                          savingDocument
                        }
                        className="w-full mt-4 bg-gradient-to-r from-emerald-600 to-teal-600 text-white py-3.5 rounded-2xl shadow-lg shadow-emerald-500/20 hover:-translate-y-0.5 transition-all disabled:opacity-60"
                      >

                        {
                          savingDocument
                            ? "Saving..."
                            : "Save Document"
                        }

                      </button>


                    </div>

                  )}


                </div>

              )}


            </div>


            <div className="group relative bg-gradient-to-br from-white via-white to-indigo-50/70 border border-slate-200/80 rounded-[30px] p-6 sm:p-8 shadow-[0_24px_75px_-35px_rgba(15,23,42,0.40)] transition-all duration-500 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-[0_34px_90px_-35px_rgba(79,70,229,0.42)]">


              <div className="flex justify-between items-center">

                <h3 className="font-bold text-xl sm:text-2xl flex gap-2 items-center tracking-tight">

                  <Sparkles
                    className="text-indigo-600"
                    size={20}
                  />

                  Ask TN Insight AI

                </h3>


                <LanguageToggle
                  language={language}
                  setLanguage={
                    setLanguage
                  }
                />

              </div>


              {uploadResult?.success && (

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-5">

                  {quickActions.map(
                    (
                      action,
                      index
                    ) => (

                      <button
                        key={index}
                        onClick={() =>
                          runQuickAction(
                            action
                          )
                        }
                        className="group/action border border-slate-200 bg-white/90 rounded-2xl px-3 py-3 text-sm font-semibold flex gap-2 items-center justify-center shadow-sm transition-all duration-300 hover:border-indigo-300 hover:bg-gradient-to-br hover:from-indigo-50 hover:to-violet-50 hover:text-indigo-700 hover:-translate-y-1 hover:shadow-md active:translate-y-0"
                      >

                        {action.icon}

                        {action.title}

                      </button>

                    )
                  )}

                </div>

              )}


              <textarea
                value={question}
                disabled={
                  !uploadResult?.success
                }
                onChange={
                  event =>
                    setQuestion(
                      event.target.value
                    )
                }
                rows={6}
                placeholder="Ask a question about this document..."
                className="w-full mt-5 border border-slate-200 bg-white/95 rounded-3xl p-5 text-base sm:text-lg leading-7 resize-none outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 focus:shadow-xl focus:shadow-indigo-500/10 shadow-inner shadow-slate-900/[0.02] disabled:bg-slate-100 transition-all duration-300 placeholder:text-slate-400"
              />


              <button
                disabled={
                  asking
                  || !uploadResult?.success
                }
                onClick={() =>
                  askQuestion()
                }
                className="w-full mt-4 bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 text-white rounded-2xl py-4 text-base font-semibold flex gap-2 justify-center items-center shadow-xl shadow-indigo-500/25 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-indigo-500/30 active:translate-y-0 disabled:opacity-50 disabled:hover:translate-y-0"
              >

                {asking ? (
                  <>
                    <Loader2
                      className="animate-spin"
                      size={18}
                    />

                    Generating...
                  </>
                ) : (
                  <>
                    <Search size={18} />

                    Ask AI
                  </>
                )}

              </button>


            </div>


            {(aiAnswer || searchResults.length > 0) && (

              <div className="lg:col-span-2 w-full mt-8 sm:mt-10 space-y-6 animate-[fadeIn_0.35s_ease-out]">

                {aiAnswer && (

                  <AIAnswer
                    answer={aiAnswer}
                    sources={sources}
                    onSourceClick={
                      openCurrentSource
                    }
                  />

                )}

                {searchResults.length > 0 && (

                  <EvidenceList
                    items={
                      searchResults
                    }
                    onSourceClick={
                      openCurrentSource
                    }
                  />

                )}

              </div>

            )}


          </div>


        </section>


        <section
          id="library"
          className="max-w-[1450px] mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20"
        >


          <div className="flex justify-between items-end gap-4 flex-wrap">

            <div>

              <p className="text-indigo-600 font-medium text-sm flex gap-2">

                <Database size={19} />

                Persistent Storage

              </p>

              <h3 className="text-3xl sm:text-4xl font-black tracking-tight mt-2">

                Your Private Document Library

              </h3>

            </div>


            <button
              onClick={fetchLibrary}
              className="border border-slate-200 bg-white rounded-2xl px-4 py-2.5 flex gap-2 shadow-sm hover:border-indigo-200 hover:text-indigo-700 transition-all"
            >

              <RefreshCw
                size={17}
              />

              Refresh

            </button>

          </div>


          <div className="grid md:grid-cols-4 gap-3 bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-3xl p-5 mt-6 shadow-lg shadow-slate-900/5">

            <Input
              value={librarySearch}
              setValue={
                setLibrarySearch
              }
              placeholder="Search..."
            />


            <Filter
              value={
                departmentFilter
              }
              setValue={
                setDepartmentFilter
              }
              options={
                departments
              }
            />


            <Filter
              value={
                typeFilter
              }
              setValue={
                setTypeFilter
              }
              options={
                documentTypes
              }
            />


            <Filter
              value={
                yearFilter
              }
              setValue={
                setYearFilter
              }
              options={
                years
              }
            />

          </div>


          {libraryLoading ? (

            <p className="text-center py-12">

              Loading...

            </p>

          ) : (

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 mt-6">

              {filteredLibrary.length === 0 && (

                <div className="md:col-span-2 lg:col-span-3 border-2 border-dashed border-slate-200 rounded-[28px] bg-white/60 p-10 text-center">

                  <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">

                    <Library size={24} />

                  </div>

                  <h4 className="text-xl font-bold mt-4">

                    No documents found

                  </h4>

                  <p className="text-slate-500 mt-2">

                    Upload and save a government PDF to build your private document library.

                  </p>

                </div>

              )}

              {filteredLibrary.map(
                document => (

                  <LibraryCard
                    key={
                      document.id
                    }
                    document={
                      document
                    }
                    loading={
                      loadingDocumentId
                      === document.id
                    }
                    deleting={
                      deletingDocumentId
                      === document.id
                    }
                    onLoad={() =>
                      loadLibraryDocument(
                        document
                      )
                    }
                    onDelete={() =>
                      deleteLibraryDocument(
                        document
                      )
                    }
                    onView={() => {

                      if (
                        !document
                          .pdf_available
                      ) {

                        alert(
                          "Original PDF unavailable for this older entry. Re-upload it once."
                        );

                        return;

                      }

                      openViewer(
                        `${API_BASE}/library/${document.id}/pdf`,
                        1,
                        document.filename
                      );

                    }}
                  />

                )
              )}

            </div>

          )}


        </section>


        <section
          id="compare"
          className="max-w-[1450px] mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20"
        >


          <div className="bg-white/85 backdrop-blur-xl border border-slate-200/80 rounded-[30px] p-6 sm:p-8 shadow-[0_24px_70px_-40px_rgba(15,23,42,0.45)]">


            <div className="flex justify-between gap-5 flex-wrap">

              <div>

                <p className="text-indigo-600 font-medium flex gap-2">

                  <GitCompareArrows
                    size={20}
                  />

                  Policy Comparison

                </p>

                <h3 className="text-3xl sm:text-4xl font-black tracking-tight mt-2">

                  Compare Government Documents

                </h3>

              </div>


              <LanguageToggle
                language={language}
                setLanguage={
                  setLanguage
                }
              />

            </div>


            <div className="grid md:grid-cols-[1fr_auto_1fr] gap-5 mt-7 items-center">

              <CompareUploadCard
                label="Document A"
                file={compareFileA}
                setFile={
                  setCompareFileA
                }
              />

              <ArrowRight
                className="hidden md:block text-indigo-600"
              />

              <CompareUploadCard
                label="Document B"
                file={compareFileB}
                setFile={
                  setCompareFileB
                }
              />

            </div>


            <button
              onClick={
                compareDocuments
              }
              disabled={
                comparing
                || !compareFileA
                || !compareFileB
              }
              className="mt-5 w-full bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 text-white py-3.5 rounded-2xl shadow-lg shadow-indigo-500/20 hover:-translate-y-0.5 transition-all disabled:opacity-50"
            >

              {
                comparing
                  ? "Comparing..."
                  : "Compare Documents"
              }

            </button>


            {comparisonResult?.success && (

              <div className="mt-7">


                <div className="bg-gradient-to-br from-indigo-50 via-violet-50/70 to-fuchsia-50/50 border border-indigo-200/80 rounded-3xl p-6 shadow-lg shadow-indigo-900/5">

                  <h4 className="font-semibold">

                    AI Comparison

                  </h4>

                  <div className="mt-5">

                    <MarkdownContent
                      content={
                        comparisonResult
                          .comparison
                      }
                    />

                  </div>

                </div>


                <div className="grid md:grid-cols-2 gap-5 mt-5">

                  <ComparisonSources
                    title={
                      comparisonResult
                        .document_a
                        .filename
                    }
                    sources={
                      comparisonResult
                        .sources_a
                    }
                    onSourceClick={
                      page =>
                        openComparisonSource(
                          "a",
                          page
                        )
                    }
                  />


                  <ComparisonSources
                    title={
                      comparisonResult
                        .document_b
                        .filename
                    }
                    sources={
                      comparisonResult
                        .sources_b
                    }
                    onSourceClick={
                      page =>
                        openComparisonSource(
                          "b",
                          page
                        )
                    }
                  />

                </div>


              </div>

            )}


          </div>


        </section>


        <section
          id="features"
          className="max-w-7xl mx-auto px-5 sm:px-6 py-16 sm:py-20"
        >

          <h3 className="text-3xl sm:text-4xl font-black tracking-tight text-center">

            Core Capabilities

          </h3>

          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-5 mt-7">

            <Feature
              title="Hybrid RAG"
              text="TF-IDF + BM25 retrieval with grounded AI answers."
            />

            <Feature
              title="Clickable Citations"
              text="Open the exact source PDF page used by the AI."
            />

            <Feature
              title="Policy Comparison"
              text="Compare two Government documents with citations."
            />

            <Feature
              title="Persistent Library"
              text="Store and reload processed government documents."
            />

            <Feature
              title="Private Workspace"
              text="Keep saved documents separated securely by your signed-in account."
            />

          </div>

        </section>





      </main>


      <footer className="relative z-10 bg-white/70 backdrop-blur-xl border-t border-slate-200/80">

        <p className="text-center text-sm text-slate-500 p-6">

          TN Insight AI is an independent academic prototype and is not affiliated with or endorsed by the Government of Tamil Nadu.

        </p>

      </footer>


      {pdfViewer.open && (

        <PdfViewer
          viewer={
            pdfViewer
          }
          onClose={() =>
            setPdfViewer(
              previous => {

                if (
                  previous.blobUrl
                ) {

                  URL.revokeObjectURL(
                    previous.blobUrl
                  );

                }

                return {
                  ...previous,
                  open: false,
                  blobUrl: ""
                };

              }
            )
          }
        />

      )}


    </div>

  );

};


const AuthScreen = ({
  mode,
  setMode,
  name,
  setName,
  email,
  setEmail,
  password,
  setPassword,
  loading,
  error,
  onSubmit
}) => (

  <div className="min-h-screen bg-slate-950 text-white relative overflow-hidden">

    <div className="absolute inset-0">

      <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-indigo-500/20 blur-3xl" />

      <div className="absolute top-1/3 -right-28 w-[28rem] h-[28rem] rounded-full bg-violet-500/20 blur-3xl" />

      <div className="absolute bottom-0 left-1/3 w-80 h-80 rounded-full bg-cyan-400/10 blur-3xl" />

    </div>

    <div className="relative min-h-screen max-w-7xl mx-auto px-6 py-10 grid lg:grid-cols-2 gap-10 items-center">

      <div className="max-w-2xl">

        <div className="inline-flex items-center gap-3">

          <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 rounded-3xl flex items-center justify-center shadow-2xl shadow-indigo-500/30">

            <Sparkles size={25} />

          </div>

          <div>

            <h1 className="text-2xl font-black">

              TN Insight AI

            </h1>

            <p className="text-sm text-white/50">

              Government Document Intelligence

            </p>

          </div>

        </div>

        <h2 className="text-4xl sm:text-5xl xl:text-6xl font-black tracking-tight leading-[1.05] mt-10">

          Your private workspace for

          <span className="block bg-gradient-to-r from-indigo-300 via-violet-300 to-fuchsia-300 bg-clip-text text-transparent mt-2">

            intelligent government documents.

          </span>

        </h2>

        <p className="text-white/60 text-lg leading-8 mt-6 max-w-xl">

          Upload, understand, compare and verify Tamil Nadu Government documents with citation-grounded AI while keeping your saved library private to your account.

        </p>

        <div className="grid sm:grid-cols-3 gap-3 mt-8">

          <AuthFeature
            icon={<ShieldCheck size={18} />}
            title="Private Library"
            text="Documents stay tied to your account."
          />

          <AuthFeature
            icon={<BookOpen size={18} />}
            title="Source Citations"
            text="Verify answers against original pages."
          />

          <AuthFeature
            icon={<Languages size={18} />}
            title="Tamil + English"
            text="Understand documents in your language."
          />

        </div>

      </div>

      <div className="lg:justify-self-end w-full max-w-md">

        <div className="bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[32px] p-6 sm:p-8 shadow-2xl shadow-black/20">

          <div className="flex bg-white/10 rounded-2xl p-1">

            <button
              onClick={() => {
                setMode("login");
              }}
              className={`flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all ${
                mode === "login"
                  ? "bg-white text-slate-950 shadow-lg"
                  : "text-white/60 hover:text-white"
              }`}
            >

              Login

            </button>

            <button
              onClick={() => {
                setMode("register");
              }}
              className={`flex-1 rounded-xl py-2.5 text-sm font-semibold transition-all ${
                mode === "register"
                  ? "bg-white text-slate-950 shadow-lg"
                  : "text-white/60 hover:text-white"
              }`}
            >

              Create Account

            </button>

          </div>

          <div className="mt-7">

            <h3 className="text-2xl font-bold">

              {
                mode === "register"
                  ? "Create your workspace"
                  : "Welcome back"
              }

            </h3>

            <p className="text-sm text-white/50 mt-2">

              {
                mode === "register"
                  ? "Create an account to keep your document library private."
                  : "Sign in to access your private TN Insight AI library."
              }

            </p>

          </div>

          <div className="space-y-4 mt-6">

            {mode === "register" && (

              <AuthInput
                icon={<UserCircle2 size={18} />}
                value={name}
                setValue={setName}
                placeholder="Full name"
                type="text"
              />

            )}

            <AuthInput
              icon={<Mail size={18} />}
              value={email}
              setValue={setEmail}
              placeholder="Email address"
              type="email"
            />

            <AuthInput
              icon={<LockKeyhole size={18} />}
              value={password}
              setValue={setPassword}
              placeholder="Password"
              type="password"
              onEnter={onSubmit}
            />

          </div>

          {error && (

            <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-400/10 text-red-200 px-4 py-3 text-sm">

              {error}

            </div>

          )}

          <button
            onClick={onSubmit}
            disabled={loading}
            className="w-full mt-6 rounded-2xl bg-gradient-to-r from-indigo-500 via-violet-500 to-fuchsia-500 py-3.5 font-semibold text-white shadow-xl shadow-indigo-500/20 hover:-translate-y-0.5 transition-all disabled:opacity-50"
          >

            {loading ? (

              <span className="inline-flex items-center gap-2">

                <Loader2
                  size={18}
                  className="animate-spin"
                />

                Please wait...

              </span>

            ) : (

              <span className="inline-flex items-center gap-2">

                {
                  mode === "register"
                    ? <UserPlus size={18} />
                    : <LogIn size={18} />
                }

                {
                  mode === "register"
                    ? "Create Account"
                    : "Login"
                }

              </span>

            )}

          </button>

          <p className="text-xs text-white/35 text-center mt-5">

            Your saved documents are isolated by account on the backend.

          </p>

        </div>

      </div>

    </div>

  </div>

);


const AuthFeature = ({
  icon,
  title,
  text
}) => (

  <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-4">

    <div className="text-indigo-300">

      {icon}

    </div>

    <p className="font-semibold text-sm mt-3">

      {title}

    </p>

    <p className="text-xs text-white/40 mt-1 leading-5">

      {text}

    </p>

  </div>

);


const AuthInput = ({
  icon,
  value,
  setValue,
  placeholder,
  type,
  onEnter
}) => (

  <div className="flex items-center gap-3 rounded-2xl border border-white/15 bg-white/10 px-4 focus-within:border-indigo-300/50 focus-within:bg-white/[0.13] transition-all">

    <div className="text-white/40">

      {icon}

    </div>

    <input
      value={value}
      type={type}
      placeholder={placeholder}
      onChange={
        event =>
          setValue(
            event.target.value
          )
      }
      onKeyDown={
        event => {

          if (
            event.key === "Enter"
            && onEnter
          ) {

            onEnter();

          }

        }
      }
      className="w-full bg-transparent py-3.5 outline-none text-white placeholder:text-white/30"
    />

  </div>

);


const PdfViewer = ({
  viewer,
  onClose
}) => {

  const [
    page,
    setPage
  ] = useState(
    viewer.page || 1
  );


  useEffect(() => {

    setPage(
      viewer.page || 1
    );

  }, [
    viewer.page,
    viewer.url
  ]);


  const pdfUrl =
    `${viewer.blobUrl || viewer.url}#page=${page}&zoom=page-width`;


  return (

    <div className="fixed inset-0 z-[100] bg-slate-950/80 backdrop-blur-sm p-3 sm:p-6">


      <div className="h-full max-w-6xl mx-auto bg-white rounded-[28px] overflow-hidden flex flex-col shadow-2xl ring-1 ring-white/20">


        <div className="flex items-center justify-between gap-4 border-b p-4">

          <div className="min-w-0">

            <h3 className="font-semibold truncate">

              {viewer.title}

            </h3>

            <p className="text-xs text-slate-500">

              Source page {page}

            </p>

          </div>


          <div className="flex gap-2 items-center">

            <button
              disabled={page <= 1}
              onClick={() =>
                setPage(
                  previous =>
                    Math.max(
                      1,
                      previous - 1
                    )
                )
              }
              className="border rounded-lg px-3 py-2 disabled:opacity-40"
            >

              Previous

            </button>


            <input
              type="number"
              min="1"
              value={page}
              onChange={
                event =>
                  setPage(
                    Math.max(
                      1,
                      Number(
                        event.target.value
                      ) || 1
                    )
                  )
              }
              className="w-20 border rounded-lg px-2 py-2 text-center"
            />


            <button
              onClick={() =>
                setPage(
                  previous =>
                    previous + 1
                )
              }
              className="border rounded-lg px-3 py-2"
            >

              Next

            </button>


            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="border rounded-lg p-2"
              title="Open in new tab"
            >

              <ExternalLink
                size={18}
              />

            </a>


            <button
              onClick={onClose}
              className="bg-slate-900 text-white rounded-lg p-2"
            >

              <X size={18} />

            </button>

          </div>

        </div>


        <iframe
          key={pdfUrl}
          src={pdfUrl}
          title="PDF Source Viewer"
          className="w-full flex-1"
        />


      </div>


    </div>

  );

};


const MarkdownContent = ({
  content
}) => (

  <div className="tn-markdown">

  <ReactMarkdown
    components={{
      h1: ({ children }) => (
        <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 mt-6 first:mt-0 mb-3">
          {children}
        </h1>
      ),

      h2: ({ children }) => (
        <h2 className="text-xl sm:text-2xl font-black tracking-tight text-slate-900 mt-6 first:mt-0 mb-3">
          {children}
        </h2>
      ),

      h3: ({ children }) => (
        <h3 className="text-lg sm:text-xl font-bold text-slate-900 mt-5 first:mt-0 mb-2">
          {children}
        </h3>
      ),

      h4: ({ children }) => (
        <h4 className="text-base sm:text-lg font-bold text-slate-900 mt-4 first:mt-0 mb-2">
          {children}
        </h4>
      ),

      p: ({ children }) => (
        <p className="text-[16px] sm:text-[17px] lg:text-[18px] leading-8 sm:leading-9 text-slate-700 font-[450] my-3 first:mt-0 last:mb-0">
          {children}
        </p>
      ),

      strong: ({ children }) => (
        <strong className="font-bold text-slate-900">
          {children}
        </strong>
      ),

      em: ({ children }) => (
        <em className="italic text-slate-700">
          {children}
        </em>
      ),

      ul: ({ children }) => (
        <ul className="list-disc pl-6 sm:pl-7 my-4 space-y-2 text-[16px] sm:text-[17px] lg:text-[18px] leading-8 sm:leading-9 text-slate-700">
          {children}
        </ul>
      ),

      ol: ({ children }) => (
        <ol className="list-decimal pl-6 sm:pl-7 my-4 space-y-2 text-[16px] sm:text-[17px] lg:text-[18px] leading-8 sm:leading-9 text-slate-700">
          {children}
        </ol>
      ),

      li: ({ children }) => (
        <li className="pl-1">
          {children}
        </li>
      ),

      blockquote: ({ children }) => (
        <blockquote className="my-4 border-l-4 border-indigo-300 bg-indigo-50/70 rounded-r-2xl px-4 py-3 text-slate-700">
          {children}
        </blockquote>
      ),

      code: ({ children }) => (
        <code className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[0.9em] font-mono text-indigo-700">
          {children}
        </code>
      ),

      hr: () => (
        <hr className="my-6 border-slate-200" />
      )
    }}
  >
    {content || ""}
  </ReactMarkdown>

  </div>

);


const AIAnswer = ({
  answer,
  sources,
  onSourceClick
}) => (

  <div className="w-full relative overflow-hidden bg-white/95 backdrop-blur-xl border border-indigo-200/80 rounded-[34px] p-6 sm:p-8 lg:p-10 xl:p-12 shadow-[0_30px_90px_-38px_rgba(79,70,229,0.42)] transition-all duration-500 hover:border-indigo-300 hover:shadow-[0_38px_110px_-38px_rgba(79,70,229,0.50)]">

    <div className="pointer-events-none absolute -top-24 -right-20 h-64 w-64 rounded-full bg-indigo-300/20 blur-3xl" />

    <div className="pointer-events-none absolute -bottom-24 left-1/4 h-56 w-56 rounded-full bg-violet-300/15 blur-3xl" />

    <div className="relative">

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">

        <div className="flex items-center gap-3">

          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-500 text-white flex items-center justify-center shadow-lg shadow-indigo-500/25">

            <Sparkles
              size={21}
            />

          </div>

          <div>

            <p className="text-xs sm:text-sm font-semibold uppercase tracking-[0.18em] text-indigo-500">

              Grounded Response

            </p>

            <h4 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900">

              AI Answer

            </h4>

          </div>

        </div>

        <div className="inline-flex items-center gap-2 self-start sm:self-auto rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1.5 text-xs sm:text-sm font-semibold text-emerald-700">

          <ShieldCheck size={15} />

          Source-grounded

        </div>

      </div>

      <div className="w-full mt-7 rounded-3xl border border-slate-200/80 bg-gradient-to-br from-slate-50/90 via-white to-indigo-50/40 p-5 sm:p-7 lg:p-9 shadow-inner shadow-slate-900/[0.02]">

        <MarkdownContent
          content={answer}
        />

      </div>

      {sources.length > 0 && (

        <div className="border-t border-indigo-100 mt-7 pt-6">

          <div className="flex flex-wrap items-center justify-between gap-3">

            <div>

              <p className="text-base sm:text-lg font-bold text-slate-900">

                Verify with original sources

              </p>

              <p className="text-sm text-slate-500 mt-1">

                Open the exact government document pages used for this response.

              </p>

            </div>

            <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 border border-indigo-100 rounded-full px-3 py-1.5">

              {sources.length} source{sources.length === 1 ? "" : "s"}

            </span>

          </div>

          <div className="flex gap-3 flex-wrap mt-4">

            {sources.map(
              (
                source,
                index
              ) => (

                <button
                  key={index}
                  onClick={() =>
                    onSourceClick(
                      source.page
                    )
                  }
                  className="group/source bg-white border border-indigo-200 text-indigo-700 rounded-2xl px-4 py-2.5 text-sm font-semibold flex gap-2 items-center shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-indigo-400 hover:bg-indigo-600 hover:text-white hover:shadow-lg hover:shadow-indigo-500/20 active:translate-y-0"
                >

                  <Eye
                    size={16}
                    className="transition-transform duration-300 group-hover/source:scale-110"
                  />

                  Page {source.page}

                  <ExternalLink
                    size={14}
                    className="opacity-60 transition-transform duration-300 group-hover/source:translate-x-0.5 group-hover/source:-translate-y-0.5"
                  />

                </button>

              )
            )}

          </div>

        </div>

      )}

    </div>

  </div>

);

const EvidenceList = ({
  items,
  onSourceClick
}) => (

  <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-[30px] p-6 sm:p-8 shadow-lg shadow-slate-900/5">

    <h4 className="text-xl sm:text-2xl font-black tracking-tight text-slate-900">

      Supporting Evidence

    </h4>

    <div className="space-y-3 mt-3">

      {items.map(
        (
          item,
          index
        ) => (

          <div
            key={index}
            className="group/evidence border border-slate-200/80 bg-white/90 rounded-2xl p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-500/10"
          >

            <button
              onClick={() =>
                onSourceClick(
                  item.page
                )
              }
              className="text-xs text-indigo-600 font-medium flex gap-1 items-center"
            >

              <Eye size={13} />

              View Page {item.page}

            </button>

            <p className="text-sm text-slate-600 whitespace-pre-wrap mt-3 max-h-40 overflow-y-auto">

              {item.text}

            </p>

          </div>

        )
      )}

    </div>

  </div>

);


const LibraryCard = ({
  document,
  loading,
  deleting,
  onLoad,
  onDelete,
  onView
}) => (

  <div className="group bg-white/90 border border-slate-200/80 rounded-3xl p-5 shadow-lg shadow-slate-900/5 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">

    <div className="flex justify-between">

      <FileText
        className="text-indigo-600"
      />

      <span className="text-xs bg-indigo-50 text-indigo-700 rounded-full px-2 py-1">

        {document.year}

      </span>

    </div>

    <h4 className="font-semibold mt-4">

      {document.title}

    </h4>

    <p className="text-xs text-slate-400 break-all mt-1">

      {document.filename}

    </p>

    <div className="flex flex-wrap gap-2 mt-3">

      <Tag>
        {document.department}
      </Tag>

      <Tag>
        {document.document_type}
      </Tag>

      <Tag>
        {document.total_pages} pages
      </Tag>

    </div>

    <div className="grid grid-cols-3 gap-2 mt-5">

      <button
        onClick={onLoad}
        disabled={loading}
        className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-xl py-2.5 text-sm font-medium shadow-md shadow-indigo-500/15 hover:-translate-y-0.5 transition-all disabled:opacity-50"
      >

        {
          loading
            ? "Loading"
            : "Ask AI"
        }

      </button>

      <button
        onClick={onView}
        className="border border-slate-200 bg-white rounded-xl py-2.5 text-sm flex gap-1 justify-center items-center hover:border-indigo-200 hover:text-indigo-700 transition-all"
      >

        <Eye size={15} />

        View

      </button>

      <button
        onClick={onDelete}
        disabled={deleting}
        className="border border-red-200 bg-red-50/50 text-red-600 rounded-xl py-2.5 text-sm hover:bg-red-50 transition-all disabled:opacity-50"
      >

        <Trash2
          size={15}
          className="inline mr-1"
        />

        Delete

      </button>

    </div>

  </div>

);


const ComparisonSources = ({
  title,
  sources,
  onSourceClick
}) => (

  <div className="group bg-white/90 border border-slate-200/80 rounded-3xl p-5 shadow-lg shadow-slate-900/5 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">

    <p className="font-medium break-all">

      {title}

    </p>

    <p className="text-xs text-slate-400 mt-1">

      Click a page to open the original PDF.

    </p>

    <div className="flex gap-2 flex-wrap mt-3">

      {sources?.map(
        (
          source,
          index
        ) => (

          <button
            key={index}
            onClick={() =>
              onSourceClick(
                source.page
              )
            }
            className="bg-indigo-50 border border-indigo-100 text-indigo-700 rounded-full px-3 py-1.5 text-xs font-medium flex gap-1 items-center hover:bg-indigo-100 transition-all"
          >

            <Eye size={13} />

            Page {source.page}

          </button>

        )
      )}

    </div>

  </div>

);


const CompareUploadCard = ({
  label,
  file,
  setFile
}) => (

  <div className="group border-2 border-dashed border-slate-300 hover:border-indigo-400 bg-slate-50/70 hover:bg-indigo-50/60 rounded-3xl p-7 text-center transition-all duration-300">

    <FileText
      className="mx-auto text-indigo-600"
    />

    <p className="font-semibold mt-3">

      {label}

    </p>

    {file ? (

      <>

        <p className="text-sm text-slate-500 mt-2 break-all">

          {file.name}

        </p>

        <button
          onClick={() =>
            setFile(null)
          }
          className="text-red-500 text-xs mt-3"
        >

          Remove

        </button>

      </>

    ) : (

      <label className="text-indigo-600 text-sm cursor-pointer mt-3 inline-block">

        Select PDF

        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={
            event =>
              setFile(
                event.target
                  .files[0]
                || null
              )
          }
        />

      </label>

    )}

  </div>

);


const LanguageToggle = ({
  language,
  setLanguage
}) => (

  <div className="bg-slate-100/90 border border-slate-200 p-1 rounded-xl flex shadow-inner">

    {[
      "English",
      "Tamil"
    ].map(
      option => (

        <button
          key={option}
          onClick={() =>
            setLanguage(
              option
            )
          }
          className={`px-3 py-1.5 rounded-lg text-xs ${
            language === option
              ? "bg-white text-indigo-700 shadow-sm ring-1 ring-slate-200"
              : "text-slate-500"
          }`}
        >

          {
            option === "Tamil"
              ? "தமிழ்"
              : option
          }

        </button>

      )
    )}

  </div>

);


const InfoCard = ({
  title,
  value
}) => (

  <div className="bg-white/90 border border-emerald-100 rounded-2xl p-3.5 shadow-sm">

    <p className="text-xs text-slate-500">

      {title}

    </p>

    <p className="font-semibold text-base mt-1.5 break-all text-slate-800">

      {value}

    </p>

  </div>

);


const Input = ({
  value,
  setValue,
  placeholder
}) => (

  <input
    value={value}
    onChange={
      event =>
        setValue(
          event.target.value
        )
    }
    placeholder={placeholder}
    className="border border-slate-200 bg-white/90 rounded-2xl px-3.5 py-3 outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition"
  />

);


const Filter = ({
  value,
  setValue,
  options
}) => (

  <select
    value={value}
    onChange={
      event =>
        setValue(
          event.target.value
        )
    }
    className="border border-slate-200 bg-white/90 rounded-2xl px-3.5 py-3 outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition"
  >

    {options.map(
      option => (

        <option
          key={option}
        >

          {option}

        </option>

      )
    )}

  </select>

);


const Tag = ({
  children
}) => (

  <span className="bg-slate-100/90 border border-slate-200/80 text-slate-600 text-xs font-medium rounded-full px-2.5 py-1">

    {children}

  </span>

);


const DocumentEvaluationCard = ({
  item
}) => {

  const evaluation =
    item?.evaluation || {};

  const comparison =
    item?.retriever_comparison || {};

  const hybrid =
    comparison?.hybrid || {};

  return (

    <div className="border border-slate-200/80 rounded-3xl p-5 bg-gradient-to-br from-white to-slate-50 shadow-lg shadow-slate-900/5">

      <div className="flex items-start justify-between gap-3">

        <div>

          <p className="font-semibold break-all">

            {item.document}

          </p>

          <p className="text-xs text-slate-500 mt-1">

            {evaluation.total_questions || 0} questions
            {item.total_pages
              ? ` • ${item.total_pages} pages`
              : ""}

          </p>

        </div>

        <span className="text-xs bg-white border rounded-full px-2 py-1">

          Hybrid

        </span>

      </div>

      <div className="grid grid-cols-2 gap-3 mt-5">

        <MiniMetric
          title="Recall@1"
          value={
            `${Math.round(
              Number(
                evaluation.recall_at_1 || 0
              ) * 100
            )}%`
          }
        />

        <MiniMetric
          title="Recall@3"
          value={
            `${Math.round(
              Number(
                evaluation.recall_at_3 || 0
              ) * 100
            )}%`
          }
        />

        <MiniMetric
          title="Recall@5"
          value={
            `${Math.round(
              Number(
                evaluation.recall_at_5 || 0
              ) * 100
            )}%`
          }
        />

        <MiniMetric
          title="MRR"
          value={
            Number(
              evaluation.mrr || 0
            ).toFixed(2)
          }
        />

      </div>

      <div className="mt-5">

        <div className="flex justify-between text-xs text-slate-500">

          <span>
            Hybrid Recall@1
          </span>

          <span>
            {Math.round(
              Number(
                hybrid.recall_at_1 || 0
              ) * 100
            )}%
          </span>

        </div>

        <div className="h-2 bg-slate-200 rounded-full mt-2 overflow-hidden">

          <div
            className="h-full bg-indigo-600 rounded-full"
            style={{
              width:
                `${Math.round(
                  Number(
                    hybrid.recall_at_1 || 0
                  ) * 100
                )}%`
            }}
          />

        </div>

      </div>

    </div>

  );

};


const MiniMetric = ({
  title,
  value
}) => (

  <div className="bg-white/95 border border-slate-200/80 rounded-2xl p-3.5 shadow-sm">

    <p className="text-xs text-slate-500">
      {title}
    </p>

    <p className="font-bold text-lg mt-1 text-indigo-600">
      {value}
    </p>

  </div>

);


const EvaluationInfoCard = ({
  icon,
  title,
  value
}) => (

  <div className="border border-slate-200/80 rounded-3xl p-4 bg-gradient-to-br from-white to-slate-50 shadow-md shadow-slate-900/5">

    <div className="text-indigo-600">
      {icon}
    </div>

    <p className="text-xs text-slate-500 mt-3">
      {title}
    </p>

    <p className="font-semibold mt-1 break-words">
      {value}
    </p>

  </div>

);


const MetricCard = ({
  title,
  value,
  description,
  percentage = true
}) => {

  const displayValue =
    percentage
      ? `${Math.round(
          Number(value) * 100
        )}%`
      : Number(value).toFixed(2);

  return (

    <div className="border border-slate-200/80 rounded-3xl p-5 bg-gradient-to-br from-white to-slate-50 shadow-lg shadow-slate-900/5">

      <p className="text-sm text-slate-500">
        {title}
      </p>

      <p className="text-3xl font-bold mt-2 text-indigo-600">
        {displayValue}
      </p>

      <p className="text-xs text-slate-400 mt-2">
        {description}
      </p>

    </div>

  );

};


const RetrieverComparisonTable = ({
  comparison
}) => {

  const methods = [
    ["TF-IDF", comparison?.tfidf],
    ["BM25", comparison?.bm25],
    ["Hybrid", comparison?.hybrid]
  ];

  return (

    <div className="border border-slate-200/80 rounded-3xl p-5 bg-white/90 shadow-lg shadow-slate-900/5">

      <h4 className="font-semibold">
        Retriever Comparison
      </h4>

      <p className="text-xs text-slate-500 mt-1">
        Higher values indicate stronger retrieval performance.
      </p>

      <div className="overflow-x-auto mt-4">

        <table className="w-full text-sm">

          <thead className="text-slate-500">

            <tr>

              <th className="text-left py-2">
                Method
              </th>

              <th className="text-right py-2">
                R@1
              </th>

              <th className="text-right py-2">
                R@3
              </th>

              <th className="text-right py-2">
                R@5
              </th>

              <th className="text-right py-2">
                MRR
              </th>

            </tr>

          </thead>

          <tbody>

            {methods.map(
              ([name, values]) => (

                <tr
                  key={name}
                  className="border-t"
                >

                  <td className="py-3 font-medium">
                    {name}
                  </td>

                  <td className="py-3 text-right">
                    {Math.round(
                      Number(
                        values?.recall_at_1 || 0
                      ) * 100
                    )}%
                  </td>

                  <td className="py-3 text-right">
                    {Math.round(
                      Number(
                        values?.recall_at_3 || 0
                      ) * 100
                    )}%
                  </td>

                  <td className="py-3 text-right">
                    {Math.round(
                      Number(
                        values?.recall_at_5 || 0
                      ) * 100
                    )}%
                  </td>

                  <td className="py-3 text-right">
                    {Number(
                      values?.mrr || 0
                    ).toFixed(2)}
                  </td>

                </tr>

              )
            )}

          </tbody>

        </table>

      </div>

    </div>

  );

};


const RetrieverBars = ({
  comparison
}) => {

  const methods = [
    {
      name: "TF-IDF",
      value:
        comparison?.tfidf
          ?.recall_at_1 || 0
    },
    {
      name: "BM25",
      value:
        comparison?.bm25
          ?.recall_at_1 || 0
    },
    {
      name: "Hybrid",
      value:
        comparison?.hybrid
          ?.recall_at_1 || 0
    }
  ];

  return (

    <div className="border border-slate-200/80 rounded-3xl p-5 bg-white/90 shadow-lg shadow-slate-900/5">

      <h4 className="font-semibold">
        Recall@1 Visualization
      </h4>

      <p className="text-xs text-slate-500 mt-1">
        Percentage of questions whose correct page ranked first.
      </p>

      <div className="space-y-5 mt-5">

        {methods.map(
          method => (

            <div key={method.name}>

              <div className="flex justify-between text-sm">

                <span className="font-medium">
                  {method.name}
                </span>

                <span className="text-slate-500">
                  {Math.round(
                    method.value * 100
                  )}%
                </span>

              </div>

              <div className="h-3 bg-slate-100 rounded-full mt-2 overflow-hidden">

                <div
                  className="h-full bg-indigo-600 rounded-full"
                  style={{
                    width:
                      `${Math.round(
                        method.value * 100
                      )}%`
                  }}
                />

              </div>

            </div>

          )
        )}

      </div>

    </div>

  );

};


const Feature = ({
  title,
  text
}) => (

  <div className="group bg-white/90 border border-slate-200/80 rounded-3xl p-5 shadow-lg shadow-slate-900/5 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">

    <h4 className="font-bold text-lg text-slate-900 group-hover:text-indigo-700 transition-colors">

      {title}

    </h4>

    <p className="text-base text-slate-600 leading-7 mt-2">

      {text}

    </p>

  </div>

);


export default App;
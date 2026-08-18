document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    lucide.createIcons();

    // Application State
    let appConfig = {};
    let currentCostData = null;
    let aiAnalysisData = null;

    // DOM Elements - Main Layout
    const btnSettings = document.getElementById('btnSettings');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // DOM Elements - Manual Tab
    const formManual = document.getElementById('formManual');
    const inputGrams = document.getElementById('inputGrams');
    const inputHours = document.getElementById('inputHours');
    const inputMinutes = document.getElementById('inputMinutes');

    // DOM Elements - Image Tab
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const uploadPreview = document.getElementById('uploadPreview');
    const previewImg = document.getElementById('previewImg');
    const btnBrowse = document.getElementById('btnBrowse');
    const btnRemoveImg = document.getElementById('btnRemoveImg');
    const btnAnalyze = document.getElementById('btnAnalyze');
    const aiStatus = document.getElementById('aiStatus');
    const aiStatusText = document.getElementById('aiStatusText');

    // DOM Elements - Results Card
    const emptyState = document.getElementById('emptyState');
    const resultsContent = document.getElementById('resultsContent');
    const subtotalPrice = document.getElementById('subtotalPrice');
    const costFilament = document.getElementById('costFilament');
    const costEnergy = document.getElementById('costEnergy');
    const costAmortization = document.getElementById('costAmortization');
    const costMaintenance = document.getElementById('costMaintenance');

    // DOM Elements - Pricing Calculations
    const profitPercent = document.getElementById('profitPercent');
    const profitValue = document.getElementById('profitValue');
    const profitSlider = document.getElementById('profitSlider');
    const retailPrice = document.getElementById('retailPrice');

    // DOM Elements - AI Benchmark
    const aiBenchmarkCard = document.getElementById('aiBenchmarkCard');
    const benchmarkRange = document.getElementById('benchmarkRange');
    const benchmarkExplanation = document.getElementById('benchmarkExplanation');
    const meterFill = document.getElementById('meterFill');
    const meterStatus = document.getElementById('meterStatus');

    // DOM Elements - Settings Sidebar
    const settingsSidebar = document.getElementById('settingsSidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const btnSaveCloseSettings = document.getElementById('btnSaveCloseSettings');
    const formSettings = document.getElementById('formSettings');
    const setFilamentCost = document.getElementById('setFilamentCost');
    const setKwhCost = document.getElementById('setKwhCost');
    const setExchangeRate = document.getElementById('setExchangeRate');
    const setPrinterCost = document.getElementById('setPrinterCost');
    const setPrinterLifespan = document.getElementById('setPrinterLifespan');
    const setMaintenancePercent = document.getElementById('setMaintenancePercent');
    const setGeminiKey = document.getElementById('setGeminiKey');
    const btnToggleKey = document.getElementById('btnToggleKey');

    // DOM Elements - Toast
    const toast = document.getElementById('toast');

    /* -------------------------------------------------------------
       Configuration Loading
       ------------------------------------------------------------- */
    async function loadConfiguration() {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) throw new Error("No se pudo obtener la configuración");
            appConfig = await response.json();
            
            // Populate settings form
            setFilamentCost.value = appConfig.costo_filamento_kg;
            setKwhCost.value = appConfig.costo_kwh;
            setExchangeRate.value = appConfig.cotizacion_dolar;
            setPrinterCost.value = appConfig.impresora_costo_usd;
            setPrinterLifespan.value = appConfig.impresora_vida_util_hs;
            setMaintenancePercent.value = appConfig.mantenimiento_porcentaje;
            setGeminiKey.value = appConfig.gemini_api_key || "";
            
            // Set default markup in profit fields
            profitPercent.value = appConfig.rentabilidad_defecto || 100;
            profitSlider.value = appConfig.rentabilidad_defecto || 100;
            
        } catch (error) {
            showToast("⚠️ Error al conectar con el servidor backend");
            console.error(error);
        }
    }

    /* -------------------------------------------------------------
       Tab Navigation Logic
       ------------------------------------------------------------- */
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`tab-${targetTab}`).classList.add('active');
        });
    });

    /* -------------------------------------------------------------
       Manual Calculation Form Submission
       ------------------------------------------------------------- */
    formManual.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const grams = parseFloat(inputGrams.value);
        const hours = parseInt(inputHours.value) || 0;
        const minutes = parseInt(inputMinutes.value) || 0;

        if (isNaN(grams) || grams < 0) {
            showToast("Por favor, ingresa un peso de filamento válido.");
            return;
        }
        if (hours === 0 && minutes === 0) {
            showToast("El tiempo de impresión debe ser mayor a 0 minutos.");
            return;
        }

        try {
            const response = await fetch('/api/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ grams, hours, minutes })
            });

            if (!response.ok) throw new Error("Error en el cálculo");

            currentCostData = await response.json();
            renderResults();
        } catch (error) {
            showToast("❌ Error al realizar los cálculos");
            console.error(error);
        }
    });

    /* -------------------------------------------------------------
       Results Rendering & Formatting
       ------------------------------------------------------------- */
    function formatCurrency(val) {
        return new Intl.NumberFormat('es-AR', {
            style: 'currency',
            currency: 'ARS',
            minimumFractionDigits: 2
        }).format(val);
    }

    function renderResults() {
        if (!currentCostData) return;

        // Hide Empty State, Show Results
        emptyState.style.display = 'none';
        resultsContent.style.display = 'block';

        // Set Costs Breakdowns
        subtotalPrice.textContent = formatCurrency(currentCostData.subtotal);
        costFilament.textContent = formatCurrency(currentCostData.breakdown.filament);
        costEnergy.textContent = formatCurrency(currentCostData.breakdown.energy);
        costAmortization.textContent = formatCurrency(currentCostData.breakdown.amortization);
        costMaintenance.textContent = formatCurrency(currentCostData.breakdown.maintenance);

        // Calculate retail price based on current profit percent
        const percent = parseFloat(profitPercent.value) || 0;
        recalculateProfitFromPercent(percent);

        // Handle AI Benchmark rendering
        if (aiAnalysisData && aiAnalysisData.price_benchmark_min && aiAnalysisData.price_benchmark_max) {
            aiBenchmarkCard.style.display = 'block';
            benchmarkRange.textContent = `${formatCurrency(aiAnalysisData.price_benchmark_min)} - ${formatCurrency(aiAnalysisData.price_benchmark_max)}`;
            benchmarkExplanation.textContent = aiAnalysisData.benchmark_explanation;
            updatePriceMeter();
        } else {
            aiBenchmarkCard.style.display = 'none';
        }
        
        // Refresh icons just in case
        lucide.createIcons();
    }

    /* -------------------------------------------------------------
       Interactive Profitability Calculations
       ------------------------------------------------------------- */
    function recalculateProfitFromPercent(percent) {
        if (!currentCostData) return;
        
        const subtotal = currentCostData.subtotal;
        const profitVal = subtotal * (percent / 100);
        const finalPrice = subtotal + profitVal;

        profitPercent.value = percent.toFixed(0);
        profitSlider.value = percent.toFixed(0);
        profitValue.value = profitVal.toFixed(2);
        retailPrice.textContent = formatCurrency(finalPrice);
        
        updatePriceMeter(finalPrice);
    }

    function recalculateProfitFromValue(val) {
        if (!currentCostData) return;

        const subtotal = currentCostData.subtotal;
        let percent = 0;
        if (subtotal > 0) {
            percent = (val / subtotal) * 100;
        }
        const finalPrice = subtotal + val;

        profitPercent.value = percent.toFixed(0);
        profitSlider.value = percent.toFixed(0);
        retailPrice.textContent = formatCurrency(finalPrice);

        updatePriceMeter(finalPrice);
    }

    profitSlider.addEventListener('input', (e) => {
        recalculateProfitFromPercent(parseFloat(e.target.value));
    });

    profitPercent.addEventListener('input', (e) => {
        let percent = parseFloat(e.target.value);
        if (isNaN(percent) || percent < 0) percent = 0;
        
        // Update slider max if needed dynamically
        if (percent > parseFloat(profitSlider.max)) {
            profitSlider.max = Math.ceil(percent / 100) * 100;
        }
        recalculateProfitFromPercent(percent);
    });

    profitValue.addEventListener('input', (e) => {
        let val = parseFloat(e.target.value);
        if (isNaN(val) || val < 0) val = 0;
        recalculateProfitFromValue(val);
    });

    /* Price Meter positioning */
    function updatePriceMeter(finalPrice) {
        if (!aiAnalysisData || !aiAnalysisData.price_benchmark_min || !aiAnalysisData.price_benchmark_max) return;
        
        const price = finalPrice || (currentCostData ? currentCostData.subtotal + parseFloat(profitValue.value) : 0);
        const min = aiAnalysisData.price_benchmark_min;
        const max = aiAnalysisData.price_benchmark_max;

        let percentage = 0;
        let statusText = "";
        let colorClass = "";

        if (price < min) {
            // Below minimum
            percentage = 15; // Initial low indicator
            statusText = "Económico (Bajo el mercado)";
            meterFill.style.background = "#8ebf8d"; // Soft pastel green
        } else if (price > max) {
            // Above maximum
            percentage = 85; // High indicator
            statusText = "Premium (Sobre el mercado)";
            meterFill.style.background = "#c94c4c"; // Red
        } else {
            // Within competitive range
            const range = max - min;
            const diff = price - min;
            percentage = 20 + (diff / range) * 60; // scale between 20% and 80%
            statusText = "Precio Competitivo";
            meterFill.style.background = "linear-gradient(to right, #8ebf8d, var(--color-accent))";
        }

        meterFill.style.width = `${percentage}%`;
        meterStatus.textContent = statusText;
    }

    /* -------------------------------------------------------------
       Image Drag & Drop / Upload Logic
       ------------------------------------------------------------- */
    // Trigger file browse
    btnBrowse.addEventListener('click', () => fileInput.click());
    
    // File input selection
    fileInput.addEventListener('change', handleFileSelect);

    // Drag events
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    function handleFileSelect() {
        const file = fileInput.files[0];
        if (!file) return;

        // Preview File
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            uploadPrompt.style.display = 'none';
            uploadPreview.style.display = 'block';
            btnAnalyze.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    btnRemoveImg.addEventListener('click', (e) => {
        e.stopPropagation(); // Avoid triggering browse
        fileInput.value = "";
        previewImg.src = "";
        uploadPreview.style.display = 'none';
        uploadPrompt.style.display = 'flex';
        btnAnalyze.disabled = true;
    });

    /* IA Analysis Request */
    btnAnalyze.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        // UI status change
        btnAnalyze.disabled = true;
        dropzone.style.pointerEvents = 'none';
        btnRemoveImg.style.display = 'none';
        aiStatus.style.display = 'flex';
        aiStatusText.textContent = "IA: Subiendo y analizando imagen...";

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/analyze-image', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (!response.ok) {
                // If it needs API Key
                if (data.needs_api_key) {
                    showToast("🔑 Por favor, configura tu API Key de Gemini en Ajustes");
                    openSettingsPanel();
                } else {
                    throw new Error(data.error || "Error al procesar la imagen");
                }
                return;
            }

            showToast("✨ ¡IA analizó la imagen correctamente!");
            
            // Save AI analysis to state
            aiAnalysisData = data.analysis;

            // Populate form fields with detected/estimated data
            inputGrams.value = aiAnalysisData.weight_grams.toFixed(2);
            inputHours.value = aiAnalysisData.time_hours;
            inputMinutes.value = aiAnalysisData.time_minutes;

            // Shift tab back to manual to show the inputs and submit
            const manualTabBtn = document.querySelector('.tab-btn[data-tab="manual"]');
            manualTabBtn.click();

            // Submit the form manually
            formManual.dispatchEvent(new Event('submit'));

        } catch (error) {
            showToast(`❌ Error: ${error.message}`);
            console.error(error);
        } finally {
            // Restore upload UI
            aiStatus.style.display = 'none';
            dropzone.style.pointerEvents = 'auto';
            btnRemoveImg.style.display = 'block';
            btnAnalyze.disabled = false;
        }
    });

    /* -------------------------------------------------------------
       Settings Sidebar Logic
       ------------------------------------------------------------- */
    function openSettingsPanel() {
        settingsSidebar.classList.add('active');
        sidebarOverlay.classList.add('active');
    }

    function closeSettingsPanel() {
        settingsSidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
    }

    btnSettings.addEventListener('click', openSettingsPanel);
    sidebarOverlay.addEventListener('click', closeSettingsPanel);
    btnSaveCloseSettings.addEventListener('click', () => {
        // Trigger submit
        formSettings.dispatchEvent(new Event('submit'));
    });

    btnToggleKey.addEventListener('click', () => {
        if (setGeminiKey.type === 'password') {
            setGeminiKey.type = 'text';
            btnToggleKey.innerHTML = '<i data-lucide="eye-off"></i>';
        } else {
            setGeminiKey.type = 'password';
            btnToggleKey.innerHTML = '<i data-lucide="eye"></i>';
        }
        lucide.createIcons();
    });

    formSettings.addEventListener('submit', async (e) => {
        e.preventDefault();

        const updatedConfig = {
            costo_filamento_kg: parseFloat(setFilamentCost.value),
            costo_kwh: parseFloat(setKwhCost.value),
            cotizacion_dolar: parseFloat(setExchangeRate.value),
            impresora_costo_usd: parseFloat(setPrinterCost.value),
            impresora_vida_util_hs: parseFloat(setPrinterLifespan.value),
            mantenimiento_porcentaje: parseFloat(setMaintenancePercent.value),
            gemini_api_key: setGeminiKey.value.trim()
        };

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedConfig)
            });

            if (!response.ok) throw new Error("Error al guardar la configuración");

            const data = await response.json();
            appConfig = data.config;
            showToast("💾 Configuración guardada correctamente");
            closeSettingsPanel();

            // Recalculate if there are inputs filled
            if (inputGrams.value && (inputHours.value || inputMinutes.value)) {
                formManual.dispatchEvent(new Event('submit'));
            }
        } catch (error) {
            showToast("❌ Error al guardar la configuración");
            console.error(error);
        }
    });

    /* -------------------------------------------------------------
       Utility Toast Notifications
       ------------------------------------------------------------- */
    let toastTimeout = null;
    function showToast(msg) {
        toast.textContent = msg;
        toast.classList.add('show');

        if (toastTimeout) clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            toast.classList.remove('show');
        }, 3500);
    }

    // Startup Call
    loadConfiguration();
});

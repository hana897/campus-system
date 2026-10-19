import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Html5Qrcode } from 'html5-qrcode';
import { useSecurity } from '../../context/SecurityContext';
import { verificationService } from '../../services/verificationService';
import { AuthenticatedImage } from '../../components/common/AuthenticatedImage';
import { Asset, VerificationLog } from '../../types';
import { assetCodeSchema, extractAssetCode } from '../../utils/validation';
import { AlertCircle, Barcode, CalendarDays, Camera, Check, ChevronRight, Clock3, Eye, Home, Info, MapPin, QrCode, Search, ShieldCheck, UserRound, X } from 'lucide-react';

export const VerificationTerminalPage: React.FC = () => {
  const { currentGate, currentUser, showToast } = useSecurity();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [inputCode, setInputCode] = useState('');
  const [activeTab, setActiveTab] = useState<'scan' | 'code'>('scan');
  const [isScanning, setIsScanning] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [latestLog, setLatestLog] = useState<VerificationLog | undefined>();
  const [verificationResult, setVerificationResult] = useState<'idle' | 'found' | 'not-found' | 'error'>('idle');
  const [notFoundCode, setNotFoundCode] = useState('');
  const [verificationError, setVerificationError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const scannerRef = useRef<Html5Qrcode | null>(null);

  const handleVerify = async (code: string) => {
    const validation = assetCodeSchema.safeParse(code);
    if (!validation.success) {
      setVerificationResult('error');
      setVerificationError(validation.error.issues[0].message);
      showToast({ type: 'error', title: 'Invalid asset code', message: validation.error.issues[0].message });
      return;
    }
    const normalizedCode = validation.data;
    setVerificationError('');
    if (!normalizedCode.trim()) return;
    setIsProcessing(true);
    setSelectedAsset(null);
    setLatestLog(undefined);
    setVerificationResult('idle');
    setVerificationError('');
    try {
      const result = await verificationService.verifyCode(normalizedCode, currentGate, `${currentUser.firstName} ${currentUser.lastName}`);
      setSelectedAsset(result.asset);
      setLatestLog(result.log);
      setVerificationResult('found');
      if (result.asset.status === 'STOLEN') {
        showToast({ type: 'error', title: 'Asset exists · Security alert', message: `${result.asset.name} is registered and flagged as stolen.` });
      } else if (result.asset.status === 'AUTHORIZED') {
        showToast({ type: 'success', title: 'Asset exists', message: `${result.asset.name} is registered in the campus inventory.` });
      } else {
        showToast({ type: 'warning', title: `Asset exists · ${result.asset.status.replace('_', ' ')}`, message: `${result.asset.name} is registered but flagged for review.` });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Security service did not respond. Check terminal connection.';
      if (message.toLowerCase().includes('asset not found')) {
        setVerificationResult('not-found');
        setNotFoundCode(normalizedCode.trim());
        showToast({ type: 'error', title: 'Asset not registered', message: `No campus asset matches ${normalizedCode.trim()}.` });
      } else {
        setVerificationResult('error');
        setVerificationError(message);
        showToast({ type: 'error', title: 'Verification failed', message });
      }
    } finally {
      setIsProcessing(false);
      setInputCode('');
    }
  };

  // QR codes open /verification?code=AST-0001; verify that asset straight away.
  useEffect(() => {
    const linkedCode = searchParams.get('code');
    if (!linkedCode) return;
    setSearchParams({}, { replace: true });
    void handleVerify(linkedCode);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!isScanning) return;
    let disposed = false;
    const scanner = new Html5Qrcode('verification-qr-reader');
    scannerRef.current = scanner;
    scanner.start({ facingMode: 'environment' }, { fps: 10, qrbox: { width: 220, height: 220 } }, (decoded) => {
      if (disposed) return;
      setIsScanning(false);
      void handleVerify(extractAssetCode(decoded));
    }, () => undefined).catch((error: unknown) => {
      if (!disposed) {
        setIsScanning(false);
        showToast({ type: 'error', title: 'Camera unavailable', message: error instanceof Error ? error.message : 'Allow camera access and try again.' });
      }
    });
    return () => {
      disposed = true;
      if (scannerRef.current) {
        const activeScanner = scannerRef.current;
        scannerRef.current = null;
        void activeScanner.stop().catch(() => undefined).finally(() => activeScanner.clear());
      }
    };
  }, [isScanning]);

  const handleFormSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    void handleVerify(inputCode);
  };

  const authorized = selectedAsset?.status === 'AUTHORIZED';
  const statusTitle = selectedAsset?.status === 'AUTHORIZED' ? 'AUTHORIZED' : selectedAsset?.status === 'STOLEN' ? 'STOLEN' : selectedAsset?.status === 'LOST' ? 'LOST' : selectedAsset?.status === 'RECOVERED' ? 'RECOVERED' : 'UNDER REVIEW';
  const statusIcon = authorized ? <Check size={24} /> : <AlertCircle size={24} />;

  return (
    <div className="content-page verification-page">
      <div className="asset-breadcrumb"><button type="button" onClick={() => navigate('/')} aria-label="Home"><Home size={16} /></button><ChevronRight size={14} /><span>Verification</span></div>
      <header className="verification-heading"><div className="verification-heading-icon"><ShieldCheck size={27} /></div><div><h1>Asset Verification</h1><p>Scan an asset QR code or enter the asset code to verify the asset.</p></div></header>

      <div className="verification-layout">
        <section className="soc-card verification-scan-card">
          <div className="verification-tabs" role="tablist" aria-label="Verification method">
            <button type="button" role="tab" aria-selected={activeTab === 'scan'} className={activeTab === 'scan' ? 'active' : ''} onClick={() => { setActiveTab('scan'); setIsScanning(false); }}><QrCode size={18} /> Scan QR Code</button>
            <button type="button" role="tab" aria-selected={activeTab === 'code'} className={activeTab === 'code' ? 'active' : ''} onClick={() => { setActiveTab('code'); setIsScanning(false); setTimeout(() => inputRef.current?.focus(), 0); }}><Barcode size={18} /> Enter Asset Code</button>
          </div>

          {activeTab === 'scan' ? <>
            <div className={`verification-viewfinder ${isScanning ? 'scanning' : ''}`}>
              {isScanning ? <div id="verification-qr-reader" className="verification-camera-reader" /> : <>
                <div className="verification-scan-frame"><span /><span /><span /><span /><div><Camera size={34} /></div></div>
                <h2>Scan QR Code</h2><p>Point your camera at the asset QR code<br />to verify the asset.</p>
              </>}
            </div>
            <button type="button" className={`soc-btn ${isScanning ? 'soc-btn-danger' : 'soc-btn-primary'} verification-camera-button`} onClick={() => setIsScanning((value) => !value)}>{isScanning ? <X size={17} /> : <Camera size={17} />}{isScanning ? 'Stop Camera' : 'Start Camera'}</button>
          </> : <>
            <div className="verification-code-entry"><div className="verification-code-icon"><Barcode size={28} /></div><h2>Enter Asset Code</h2><p>Scan with a USB barcode reader or enter the asset code manually.</p>
              <form onSubmit={handleFormSubmit}><label htmlFor="verification-code">Asset Code</label><div className="verification-code-controls"><input id="verification-code" ref={inputRef} className="soc-input" placeholder="e.g. AST-0001" value={inputCode} onChange={(event) => setInputCode(event.target.value)} required /><button className="soc-btn soc-btn-primary" type="submit" disabled={isProcessing}><Search size={17} />{isProcessing ? 'Verifying…' : 'Verify Asset'}</button></div></form>
            </div>
          </>}

          {activeTab === 'scan' && <div className="verification-or"><span>OR</span></div>}
          {activeTab === 'scan' && <form className="verification-inline-code" onSubmit={handleFormSubmit}><label htmlFor="verification-code-inline">Asset Code</label><div className="verification-code-controls"><div className="verification-code-input"><Barcode size={17} /><input id="verification-code-inline" ref={inputRef} className="soc-input" placeholder="e.g. AST-0001" value={inputCode} onChange={(event) => setInputCode(event.target.value)} required /></div><button className="soc-btn soc-btn-primary" type="submit" disabled={isProcessing}><Search size={17} />{isProcessing ? 'Verifying…' : 'Verify Asset'}</button></div></form>}
        </section>

        <section className="soc-card verification-result-card" aria-live="polite">
          {selectedAsset ? <>
            <div className="verification-status-banner is-authorized"><span className="verification-status-symbol"><Check size={24} /></span><div><h2>ASSET EXISTS</h2><p>This asset is registered in the campus inventory. Current status: {statusTitle}.</p></div></div>
            <div className="verification-asset-details">
              <div className="verification-asset-summary"><div className="verification-asset-image">{selectedAsset.ownerAvatarUrl ? <AuthenticatedImage src={selectedAsset.ownerAvatarUrl} alt={`${selectedAsset.ownerName} profile`} /> : <UserRound size={38} />}</div><div className="verification-asset-title"><h2>{selectedAsset.name}</h2><span>{selectedAsset.category}</span></div><div className="verification-asset-codes"><div><small>Asset Code</small><strong>{selectedAsset.id}</strong></div><div><small>Serial Number</small><strong>{selectedAsset.serial}</strong></div></div></div>
              <div className="verification-detail-row"><UserRound size={18} /><span>Owner</span><strong>{selectedAsset.ownerName}</strong></div>
              <div className="verification-detail-row"><CalendarDays size={18} /><span>Department</span><strong>{selectedAsset.department}</strong></div>
              <div className="verification-detail-row"><MapPin size={18} /><span>Location</span><strong>{selectedAsset.notes?.match(/Campus location: ([^\n]+)/)?.[1] || currentGate}</strong></div>
              <div className="verification-detail-row"><ShieldCheck size={18} /><span>Status</span><strong><i className={authorized ? 'status-dot green' : 'status-dot amber'} />{statusTitle}</strong></div>
              <div className="verification-detail-row"><UserRound size={18} /><span>Verified By</span><strong>{currentUser.firstName} {currentUser.lastName} ({latestLog?.officerId})</strong></div>
              <div className="verification-detail-row"><Clock3 size={18} /><span>Verification Time</span><strong>{latestLog ? new Date(latestLog.timestamp).toLocaleString([], { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}</strong></div>
              <div className="verification-result-actions"><div className="soc-btn soc-btn-success" role="status"><Check size={17} /> Registered</div><button type="button" className="soc-btn soc-btn-outline" onClick={() => navigate(`/assets/${selectedAsset.id}`)}><Eye size={17} /> View Asset</button></div>
            </div>
          </> : verificationResult === 'not-found' ? <>
            <div className="verification-status-banner is-flagged"><span className="verification-status-symbol"><AlertCircle size={24} /></span><div><h2>ASSET NOT REGISTERED</h2><p>No campus asset record was found for “{notFoundCode}”.</p></div></div>
            <div className="verification-empty-state"><div><Search size={35} /></div><h2>Not in the asset registry</h2><p>Check the asset code or scan a valid campus asset QR code, then verify again.</p></div>
          </> : verificationResult === 'error' ? <>
            <div className="verification-status-banner is-flagged"><span className="verification-status-symbol"><AlertCircle size={24} /></span><div><h2>VERIFICATION UNAVAILABLE</h2><p>{verificationError}</p></div></div>
          </> : <>
            <div className="verification-empty-state"><div><ShieldCheck size={35} /></div><h2>Verification Result</h2><p>Scan a QR code or enter an asset code to view its registration, owner, and current security status.</p><span><i /> Gate: {currentGate}</span></div>
          </>}
        </section>
      </div>
      <div className="verification-safety-note"><Info size={18} /><span>A successful verification confirms the asset exists in the campus inventory. The security status is shown separately for review.</span></div>
    </div>
  );
};

import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Location } from 'react-router-dom';
import { Box, Eye, EyeOff, LockKeyhole, LogIn, QrCode, Shield, ShieldCheck, Mail } from 'lucide-react';
import { authService } from '../../services/authService';
import { useSecurity } from '../../context/SecurityContext';
import { emailSchema, passwordSchema } from '../../utils/validation';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn, showToast } = useSecurity();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const emailValidation = emailSchema.safeParse(email);
    const passwordValidation = passwordSchema.safeParse(password);

    setEmailError(emailValidation.success ? '' : emailValidation.error.issues[0].message);
    setPasswordError(passwordValidation.success ? '' : passwordValidation.error.issues[0].message);

    if (!emailValidation.success || !passwordValidation.success) {
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const { user } = await authService.login(emailValidation.data, passwordValidation.data);
      signIn(user);
      showToast({ type: 'success', title: 'Welcome back', message: `Signed in as ${user.firstName} ${user.lastName}.` });
      // Return to the page that sent the user here (e.g. a scanned QR link).
      const from = (location.state as { from?: Location } | null)?.from;
      navigate(from ? `${from.pathname}${from.search}` : '/dashboard', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Sign in failed. Check your details and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return <main className="login-page">
    <section className="login-intro">
      <div className="login-brand"><span className="login-brand-mark"><Shield size={38} /></span><span><strong>Campus PC</strong><small>Registration &amp; Exit Verification</small></span></div>
      <div className="login-intro-copy"><h1>Campus PC Registration &amp; Exit Verification System</h1><p>Securely manage register assets, verify property and authorize campus exits.</p></div>
      <div className="login-features">
        <div><span><Box size={21} /></span><section><strong>Asset management</strong><small>Register and manage university property.</small></section></div>
        <div><span><QrCode size={21} /></span><section><strong>QR verification</strong><small>Verify campus assets in a few seconds.</small></section></div>
        <div><span><ShieldCheck size={21} /></span><section><strong>Exit authorization</strong><small>Check assets before they leave campus.</small></section></div>
      </div>
      <div className="login-campus-art" aria-hidden="true"><span /><span /><span /></div>
    </section>

    <section className="login-form-side"><div className="login-form-wrap">
      <div className="login-form-heading"><h2>Welcome back</h2><p>Sign in to your account to continue.</p></div>
      {error && <div className="login-error" role="alert"><ShieldCheck size={18} /><span>{error}</span></div>}
      <form onSubmit={handleSubmit} className="login-form" noValidate>
        <label>Email Address<div className="login-input-wrap"><Mail size={18} /><input className="soc-input" type="email" value={email} onChange={(event) => { setEmail(event.target.value); if (emailError) setEmailError(''); }} placeholder="Enter your email address" autoComplete="username" aria-invalid={Boolean(emailError)} required /></div>{emailError && <small style={{ color: '#fca5a5', display: 'block', marginTop: '0.35rem' }}>{emailError}</small>}</label>
        <label>Password<div className="login-input-wrap"><LockKeyhole size={18} /><input className="soc-input" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => { setPassword(event.target.value); if (passwordError) setPasswordError(''); }} placeholder="Enter your password" autoComplete="current-password" aria-invalid={Boolean(passwordError)} required /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((show) => !show)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{passwordError && <small style={{ color: '#fca5a5', display: 'block', marginTop: '0.35rem' }}>{passwordError}</small>}</label>
        <button className="soc-btn soc-btn-primary login-submit" type="submit" disabled={isLoading}><LogIn size={18} />{isLoading ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <div className="login-assurance"><LockKeyhole size={14} />Authorized users only. Account activity is recorded.</div>
      <footer className="login-footer">© {new Date().getFullYear()} Campus PC Registration &amp; Exit Verification System<br />University Campus Security Department</footer>
    </div></section>
  </main>;
};

import { Brand } from './Brand';

export function AppFooter() {
  return <footer className="site-footer">
    <div className="container footer-layout"><Brand compact />
      <p>FUSION 2K26 <span aria-hidden="true">/</span> SPACE-02</p>
      <span className="footer-signature">FOLLOW THE EVIDENCE.</span>
    </div>
  </footer>;
}

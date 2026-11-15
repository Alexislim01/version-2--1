import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
const pins=['environment-proxy-ca.crt','mitmproxy-ca-cert.crt','nebula-mitmproxy.crt'].filter(name=>existsSync('/usr/local/share/ca-certificates/'+name)).map(name=>{const key=execFileSync('openssl',['x509','-in','/usr/local/share/ca-certificates/'+name,'-pubkey','-noout']);const der=execFileSync('openssl',['pkey','-pubin','-outform','DER'],{input:key});return createHash('sha256').update(der).digest('base64');});
export const options={headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:existsSync('/usr/bin/chromium')?{executablePath:'/usr/bin/chromium'}:{}),args:['--no-sandbox','--enable-unsafe-swiftshader','--ignore-certificate-errors-spki-list='+pins.join(',')]};

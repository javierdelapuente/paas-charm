/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.KeyManagementException;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.NoSuchProviderException;
import java.security.Security;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.jsse.provider.BouncyCastleJsseProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import com.canonical.sampleapp.web.rest.MongoUserController;

@SpringBootApplication
public class Application {
	private final Logger log = LoggerFactory.getLogger(Application.class);

	public static void main(String[] args)  {
		Logger log = LoggerFactory.getLogger(Application.class);
		try {
		CertificateFactory cf;

			cf = CertificateFactory.getInstance("X.509");

		  try (InputStream is = new FileInputStream("/app/ca.crt")) {
			  
		    X509Certificate cert = (X509Certificate) cf.generateCertificate(is);

		    // 2. Create a trust store
		    KeyStore trustStore = KeyStore.getInstance(KeyStore.getDefaultType());
		    trustStore.load(null, null);
		    trustStore.setCertificateEntry("myserver", cert);

		    // 3. Init trust manager
		    TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
		    tmf.init(trustStore);
		
		    Security.addProvider(new BouncyCastleProvider());
		    Security.insertProviderAt(new BouncyCastleJsseProvider(), 2);
		    
		    SSLContext bcSslContext = SSLContext.getInstance("TLS", "BCJSSE");
		    bcSslContext.init(null, tmf.getTrustManagers(), null);
		    
		    SSLContext.setDefault(bcSslContext);
		    HttpsURLConnection.setDefaultSSLSocketFactory(bcSslContext.getSocketFactory());
		    log.info("FINISHED CONFIGURING SSL");
		  } catch (KeyStoreException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (KeyManagementException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (NoSuchAlgorithmException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (NoSuchProviderException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		} catch (CertificateException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		  SpringApplication.run(Application.class, args);
	}
}

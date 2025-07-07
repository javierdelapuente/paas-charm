package com.canonical.sampleapp.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.web.server.SecurityWebFilterChain;
import static org.springframework.security.config.Customizer.withDefaults;

import java.util.HashSet;
import java.util.Set;

import org.springframework.security.web.SecurityFilterChain;

//@EnableWebSecurity
@ConditionalOnProperty(name = "spring.security.oauth2.client.registration.hydra.client-id")
@Configuration
public class OAuth2SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(authorize -> authorize
                .anyRequest().authenticated()
            )
            //.oauth2Login(Customizer.withDefaults());
            .oauth2Login(oauth2 -> oauth2
                    .redirectionEndpoint(redir -> redir.baseUri("/callback"))
                );

        return http.build();
    }
}

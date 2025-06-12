-- DNS Attack Detection Script for Fluent Bit
-- Detects potential DNS amplification attacks and other suspicious patterns

-- Configuration
local THRESHOLD_QPS_PER_IP = 100      -- Queries per second threshold per IP
local THRESHOLD_ANY_QUERIES = 10      -- ANY query threshold
local THRESHOLD_TXT_QUERIES = 50      -- TXT query threshold
local TIME_WINDOW = 60                -- Time window in seconds

-- State tracking
local query_counts = {}
local suspicious_ips = {}

function detect_attack(tag, timestamp, record)
    local client_ip = record["client"]
    local query_type = record["qtype"]
    local domain = record["qname"]
    local current_time = os.time()
    
    -- Initialize IP tracking if needed
    if not query_counts[client_ip] then
        query_counts[client_ip] = {
            total = 0,
            any_queries = 0,
            txt_queries = 0,
            first_seen = current_time,
            last_seen = current_time
        }
    end
    
    local ip_data = query_counts[client_ip]
    
    -- Update counters
    ip_data.total = ip_data.total + 1
    ip_data.last_seen = current_time
    
    if query_type == "ANY" then
        ip_data.any_queries = ip_data.any_queries + 1
    elseif query_type == "TXT" then
        ip_data.txt_queries = ip_data.txt_queries + 1
    end
    
    -- Calculate QPS
    local time_diff = current_time - ip_data.first_seen
    if time_diff > 0 then
        local qps = ip_data.total / time_diff
        
        -- Check for attacks
        local is_suspicious = false
        local attack_type = nil
        
        -- High QPS attack
        if qps > THRESHOLD_QPS_PER_IP then
            is_suspicious = true
            attack_type = "high_qps"
            record["attack_type"] = "High QPS Attack"
            record["qps"] = string.format("%.2f", qps)
        end
        
        -- ANY query amplification attack
        if ip_data.any_queries > THRESHOLD_ANY_QUERIES then
            is_suspicious = true
            attack_type = "any_amplification"
            record["attack_type"] = "ANY Query Amplification"
            record["any_query_count"] = ip_data.any_queries
        end
        
        -- TXT query amplification attack
        if ip_data.txt_queries > THRESHOLD_TXT_QUERIES then
            is_suspicious = true
            attack_type = "txt_amplification"
            record["attack_type"] = "TXT Query Amplification"
            record["txt_query_count"] = ip_data.txt_queries
        end
        
        -- Check for DNS tunneling patterns
        if string.len(domain) > 100 or string.match(domain, "^[a-f0-9]{32,}") then
            is_suspicious = true
            attack_type = "dns_tunneling"
            record["attack_type"] = "Possible DNS Tunneling"
            record["domain_length"] = string.len(domain)
        end
        
        -- Mark as security event
        if is_suspicious then
            record["security_event"] = true
            record["severity"] = "high"
            
            -- Track suspicious IP
            suspicious_ips[client_ip] = {
                attack_type = attack_type,
                last_seen = current_time,
                query_count = ip_data.total
            }
            
            -- Modify tag to route to security output
            tag = "powerdns.security." .. attack_type
        end
    end
    
    -- Clean up old entries (simple memory management)
    if math.random() < 0.01 then  -- 1% chance to clean up
        clean_old_entries(current_time)
    end
    
    return 1, timestamp, record
end

function clean_old_entries(current_time)
    -- Remove entries older than TIME_WINDOW
    for ip, data in pairs(query_counts) do
        if current_time - data.last_seen > TIME_WINDOW then
            query_counts[ip] = nil
        end
    end
    
    for ip, data in pairs(suspicious_ips) do
        if current_time - data.last_seen > TIME_WINDOW * 2 then
            suspicious_ips[ip] = nil
        end
    end
end
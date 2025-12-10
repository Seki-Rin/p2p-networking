class Net:
    def __init__(self, ip_and_mask: tuple):
        """
        Инициализирует объект IP-сети.

        Args:
            ip_and_mask (tuple[str, str]): кортеж из двух строк:
                - первый элемент — IP-адрес хоста в сети (например, "192.168.1.100").
                - второй элемент — Маска подсети, может быть в формате CIDR (например, "24")
                  или в десятичном виде (например, "255.255.255.0").

        Raises:
            ValueError: Если IP-адрес или маска имеют неверный формат.
        """
        self.ip = ip_and_mask[0]
        self.mask = ip_and_mask[1]
        if not Net._validate_dotted_decimal_str(self.ip):
            raise ValueError('Invalid IP address format')
        if not Net._validate_dotted_decimal_str(self.mask):
            self.mask_bin = Net._cidr_to_bin(self.mask)
            if not Net._validate_cidr_prefix(self.mask):
                raise ValueError('Invalid CIDR prefix. Prefix must be between 0 and 32')
        else:
            self.mask_bin = Net._to_binary_string(self.mask)
            if not Net._validate_mask_bin(self.mask_bin):
                raise ValueError('Invalid dotted decimal mask. In a subnet mask, the bits must be contiguous: first all 1s, then all 0s.')
        self.network_address_str, self.net_address_bin = self._calculate_net(self._to_binary_string(self.ip), self.mask_bin)
        self.netmask = self._bin_to_dec(self.mask_bin)
        self.address_count = 2**self.mask_bin.count('0')
        self.broadcast_address_bin = self.net_address_bin[0:32 - self.mask_bin.count('0')] + '1' * self.mask_bin.count('0')
        self.broadcast_address = self._bin_to_dec(self.broadcast_address_bin)

    @staticmethod
    def _ip_to_int(ip):
        ip_bin = Net._to_binary_string(ip)
        return int(ip_bin, 2)
    
    @staticmethod
    def _int_to_ip(integer: int):
        return Net._bin_to_dec(bin(integer)[2:].zfill(32))

    @staticmethod
    def _validate_dotted_decimal_str(address_str:str) -> bool:
        octets = address_str.split('.')
        return len(octets) == 4 and all(o.isdigit() and 0 <= int(o) <= 255 for o in octets)
    
    @staticmethod
    def _validate_cidr_prefix(mask_str:str) -> bool:
        if (mask_str.isdigit() and 0 <= int(mask_str) <= 32):
            return True
        else:
            return False
        
    @staticmethod
    def _validate_mask_bin(mask_bin:str) -> bool:
        is_zero = False
        for i in mask_bin:
            if is_zero:
                if i == '1':
                    return False
            elif i == '0':
                is_zero = True
        return True


                        

    def __contains__(self, ip:str):
        """Возвращает True, если IP принадлежит сети, в противном случае False"""
        ip = self._to_binary_string(ip)
        ip_net_part = ''.join(str(int(x) & int(y)) for x, y in zip(ip, self.mask_bin))
        return ip_net_part == self.net_address_bin

    @staticmethod
    def _to_binary_string(address_or_prefix: str):
            return ''.join(bin(int(octet))[2:].zfill(8) for octet in address_or_prefix.split('.'))
        
    def _cidr_to_bin(prefix: str):
        return '1' * int(prefix) + '0' * (32 - int(prefix))
    
    @staticmethod
    def _bin_to_dec(ip):
            ip = '.'.join(str(int(ip[i:i+8], 2)) for i in range(0, 32, 8))
            return ip

    @staticmethod
    def _calculate_net(ip, mask):
        net_bin = ''.join(str(int(x) & int(y)) for x,y in zip(ip,mask))
        net = Net._bin_to_dec(net_bin)
        return net, net_bin

    def __iter__(self):
        """Возвращает IP, принадлежащие сети, включая адрес сети и широковещательный"""
        for x in range(Net._ip_to_int(self.network_address_str), Net._ip_to_int(self.broadcast_address)+1):
            yield Net._int_to_ip(x)
    
    def __str__(self):
        return f'{self.network_address_str}/{self.mask_bin.count("1")}'
    
    def __repr__(self):
        return f'Net({self.network_address_str},{self.netmask})'
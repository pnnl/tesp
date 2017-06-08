class curve:
    def __init__(self):
        self.bidname, self.price, self.quantity = ([] for i in range(3))
        self.count = 0
        self.total = 0.0
        self.total_on = 0.0
        self.total_off = 0.0  
        
    def set_curve_order(self, flag):
        # If the reverse of the array is required, so that the values are in ascending order
        if flag == 'ascending':
            self.price.reverse()
            self.quantity.reverse()
            self.bidname.reverse()
        
    def add_to_curve(self, price, quantity, name, state):
        if quantity == 0:
            return
        self.total += quantity
        if state == 'ON':
            self.total_on += quantity
        if state == 'OFF':
            self.total_off += quantity
        value_insert_flag = 0
        if self.count == 0:
            # Since it is the first time assigning values to the curve, define an empty array for the price and mean
            self.bidname, self.price, self.quantity = ([] for i in range(3))
            self.price.append(price)
            self.quantity.append(quantity)
            self.bidname.append(name)
            self.count += 1
        else:
            value_insert_flag = 0
            for i in range(0, self.count):
                # If the price is larger than the compared curve section price, price inserted before that section of the curve
                if price >= self.price[i]:
                    if i == 0:
                        # If the price is larger than that of all the curve sections, insert at the beginning of the curve
                        self.price.insert(0, price)
                        self.quantity.insert(0, quantity)
                        self.bidname.insert(0, name)
                    else:
                        self.price.insert(i+1, price)
                        self.quantity.insert(i+1, quantity)
                        self.bidname.insert(i+1, name)
                    self.count += 1
                    value_insert_flag = 1
                    break
        
            # If the price is smaller than that of all the curve sections, insert at the end of the curve
            if value_insert_flag == 0:                   
                self.price.append(price)
                self.quantity.append(quantity)
                self.bidname.append(name)
                self.count += 1
            
        
                            
                            
                    
                

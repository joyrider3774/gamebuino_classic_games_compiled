$(function () {

	// basic SD card emulation class
	SdDevice =
	{
		Init: function ()
		{
			var self = this;

			this.CS_PORT = AtmelContext.B; // PB2
			this.CS_BIT = 2;
			this.Index = 0;
			this.Received = [];
			for (var i = 0; i < 10; i++)
				this.Received[i] = 0;
			this.Status = 0;
			this.Buffer = [];
			for (var i = 0; i < 550; i++)
				this.Buffer[i] = 0;
			this.BytesToSend = 0;
			this.SendIndex = 0;
			this.AppCommand = false;
			this.MultiRead = false;
			this.MultiAddr = 0;
			this.WriteMode = 0;
			this.WriteAddr = 0;
			this.WriteCount = 0;
			this.WriteMulti = false;
			SPI.OnReceivedByte.push(function(data) {self.spi_OnReceivedByte(data);});
		},

		Reset: function()
		{
			this.MultiRead = false;
			this.WriteMode = 0;
			this.WriteMulti = false;
			this.Status = 0;
			this.Index = 0;
			this.BytesToSend = 0;
			this.SendIndex = 0;
		},

		// queue one data block: token, 512 bytes, two CRC bytes
		QueueBlock: function()
		{
			this.SendIndex = 0;
			this.BytesToSend = 0;
			this.Buffer[this.BytesToSend++] = 0xFE;
			for (var i = 0; i < 512; i++)
			{
				var b = this.ReadBuffer ? this.ReadBuffer[this.MultiAddr + i] : 0;
				this.Buffer[this.BytesToSend++] = (b === undefined) ? 0 : b;
			}
			this.Buffer[this.BytesToSend++] = 0x00;
			this.Buffer[this.BytesToSend++] = 0x00;
			this.MultiAddr += 512;
		},

		// Card images are stored trimmed of their trailing empty space, so a
		// write can land past the end of the buffer even though the volume
		// really is that big. Grow it rather than dropping the write.
		Grow: function(end)
		{
			if (!this.ReadBuffer || end <= this.ReadBuffer.length)
				return;
			var size = Math.max(this.ReadBuffer.length, 512);
			while (size < end)
				size *= 2;
			var grown = new Uint8Array(size);
			grown.set(this.ReadBuffer);
			this.ReadBuffer = grown;
		},

		// A write command puts the card into a data-receiving state: the host
		// clocks out a start token, 512 data bytes and two CRC bytes, and only
		// then reads the card's data response. None of those are commands, so
		// they have to bypass the command parser entirely.
		WriteByte: function(data)
		{
			switch (this.WriteMode)
			{
				case 1:		// waiting for a start token, skipping fill bytes
					if (data == 0xFE || data == 0xFC)
					{
						this.Grow(this.WriteAddr + 512);
						this.WriteCount = 0;
						this.WriteMode = 2;
					}
					else if (data == 0xFD)	// stop tran, ends a CMD25 run
					{
						this.WriteMulti = false;
						this.WriteMode = 0;
					}
					break;

				case 2:		// the 512 data bytes
					if (this.ReadBuffer && (this.WriteAddr + this.WriteCount) < this.ReadBuffer.length)
						this.ReadBuffer[this.WriteAddr + this.WriteCount] = data;
					if (++this.WriteCount == 512)
					{
						this.WriteAddr += 512;
						this.WriteCount = 0;
						this.WriteMode = 3;
					}
					break;

				case 3:		// two CRC bytes; the data response follows them
					if (++this.WriteCount == 2)
					{
						this.WriteMode = this.WriteMulti ? 1 : 0;
						this.SendIndex = 0;
						this.BytesToSend = 0;
						this.Buffer[this.BytesToSend++] = 0x05;	// data accepted
					}
					break;
			}
			SPI.ReceiveByte(0xff);
		},

		spi_OnReceivedByte: function(data)
		{
			// make sure the SD card is currently enabled
			if (this.CS_PORT.WriteRegister.get().get_bit(this.CS_BIT) != 0)
				return;

			// A multi-block read streams until the host stops it. Only start
			// the next block when the host is clocking idle bytes, so that a
			// CMD12 arriving at a block boundary is still seen as a command.
			if (this.BytesToSend == 0 && this.MultiRead && data == 0xff)
				this.QueueBlock();

			if (this.BytesToSend > 0)
			{
				this.BytesToSend--;
				SPI.ReceiveByte(this.Buffer[this.SendIndex++]);
				return;
			}

			if (this.WriteMode > 0)
			{
				this.WriteByte(data);
				return;
			}

			this.Received[this.Index++] = data;
			if (!this.AppCommand)
			{
				switch (this.Received[0])
				{
					// CMD0 - RESET
					case 0x40:
						if (this.Index == 6)
						{
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							// Ncr: a real card sends 1-8 fill bytes before its R1.
							// SdFat discards the first byte after a command for exactly
							// this reason, so answering on that byte loses the response.
							this.Buffer[this.BytesToSend++] = 0xff;
							this.Buffer[this.BytesToSend++] = 0x01;
						}
						break;

						// CMD8 - SEND_IF_COND
					case 0x40 + 8:
						if (this.Index == 6)
						{
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							// Ncr: a real card sends 1-8 fill bytes before its R1.
							// SdFat discards the first byte after a command for exactly
							// this reason, so answering on that byte loses the response.
							this.Buffer[this.BytesToSend++] = 0xff;
							// R1 = illegal command + idle. Upstream sent 0x04, dropping
							// the idle bit; a real card that does not support CMD8
							// answers 0x05 while it is still idle, and SdFat tests for
							// exactly that value before deciding the card is v1:
							//   if (cardCommand(CMD8, 0x1AA) == (R1_ILLEGAL_COMMAND | R1_IDLE_STATE))
							// With 0x04 it took the v2 branch instead, read four more
							// bytes looking for 0xAA, and failed with CMD8 error.
							this.Buffer[this.BytesToSend++] = 0x05;	// invalid, still idle
							//this.Buffer[this.BytesToSend++] = 0x00;	// R1
							//this.Buffer[this.BytesToSend++] = 0xaa;
							//this.Buffer[this.BytesToSend++] = 0xaa;
							//this.Buffer[this.BytesToSend++] = 0xaa;
							//this.Buffer[this.BytesToSend++] = 0xaa;
						}
						break;

						// CMD16 - SET_BLOCKLEN
					case 0x40 + 16:
						if (this.Index == 6)
						{
							this.Status = 0x01;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							// Ncr: a real card sends 1-8 fill bytes before its R1.
							// SdFat discards the first byte after a command for exactly
							// this reason, so answering on that byte loses the response.
							this.Buffer[this.BytesToSend++] = 0xff;
							this.Buffer[this.BytesToSend++] = 0x00;
						}
						break;

						// CMD17 - READ_SINGLE_BLOCK
					case 0x40 + 17:
						if (this.Index == 6)
						{
							this.Status = 0x01;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							// Ncr: a real card sends 1-8 fill bytes before its R1.
							// SdFat discards the first byte after a command for exactly
							// this reason, so answering on that byte loses the response.
							this.Buffer[this.BytesToSend++] = 0xff;
							this.Buffer[this.BytesToSend++] = 0x00;
							this.Buffer[this.BytesToSend++] = 0xFE;
							try
							{
								var offset = (this.Received[1] << 24) + (this.Received[2] << 16) + (this.Received[3] << 8) + this.Received[4];
								// Reading past the end of a Uint8Array yields
								// undefined rather than throwing, which would
								// clock undefined out over SPI. Card images are
								// stored trimmed of their trailing empty space,
								// so treat anything past the end as blank.
								for (var i = 0; i < 512; i++)
								{
									var b = this.ReadBuffer[offset + i];
									this.Buffer[this.BytesToSend + i] = (b === undefined) ? 0 : b;
								}
							}
							catch (e)
							{
								for (var i = 0; i < 512; i++)
									this.Buffer[this.BytesToSend + i] = 0;
							}
							this.BytesToSend += 512;
							this.Buffer[this.BytesToSend++] = 0x00;
							this.Buffer[this.BytesToSend++] = 0x00;
						}
						break;

						// CMD18 - READ_MULTIPLE_BLOCK
					case 0x40 + 18:
						if (this.Index == 6)
						{
							this.Status = 0x01;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							this.Buffer[this.BytesToSend++] = 0xff;	// Ncr
							this.Buffer[this.BytesToSend++] = 0x00;	// R1: accepted
							this.MultiAddr = (this.Received[1] << 24) + (this.Received[2] << 16)
								+ (this.Received[3] << 8) + this.Received[4];
							this.MultiRead = true;
						}
						break;

					// CMD12 - STOP_TRANSMISSION
					case 0x40 + 12:
						if (this.Index == 6)
						{
							this.MultiRead = false;
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							this.Buffer[this.BytesToSend++] = 0xff;	// stuff byte
							this.Buffer[this.BytesToSend++] = 0xff;	// Ncr
							this.Buffer[this.BytesToSend++] = 0x00;	// R1
						}
						break;

						// CMD24 - WRITE_BLOCK
					case 0x40 + 24:
						if (this.Index == 6)
						{
							this.Status = 0x01;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							this.Buffer[this.BytesToSend++] = 0xff;	// Ncr
							this.Buffer[this.BytesToSend++] = 0x00;	// R1: accepted
							this.WriteAddr = (this.Received[1] << 24) + (this.Received[2] << 16)
								+ (this.Received[3] << 8) + this.Received[4];
							this.MultiRead = false;
							this.WriteMulti = false;
							this.WriteMode = 1;
						}
						break;

						// CMD25 - WRITE_MULTIPLE_BLOCK
					case 0x40 + 25:
						if (this.Index == 6)
						{
							this.Status = 0x01;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							this.Buffer[this.BytesToSend++] = 0xff;	// Ncr
							this.Buffer[this.BytesToSend++] = 0x00;	// R1: accepted
							this.WriteAddr = (this.Received[1] << 24) + (this.Received[2] << 16)
								+ (this.Received[3] << 8) + this.Received[4];
							this.MultiRead = false;
							this.WriteMulti = true;
							this.WriteMode = 1;
						}
						break;

						// CMD13 - SEND_STATUS. SdFat checks this after every
						// write, with CHECK_FLASH_PROGRAMMING on, and wants both
						// R2 bytes zero.
					case 0x40 + 13:
						if (this.Index == 6)
						{
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							this.Buffer[this.BytesToSend++] = 0xff;	// Ncr
							this.Buffer[this.BytesToSend++] = 0x00;	// R2 low
							this.Buffer[this.BytesToSend++] = 0x00;	// R2 high
						}
						break;

					// CMD23 - Number of blocks
					case 0x40 + 23:
						if (this.Index == 6)
						{
							this.Status = 0x01;
							this.Index = 0;
						}
						break;

						// CMD55 - ACMD
					case 0x40 + 55:
						if (this.Index == 6)
						{
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							// Ncr: a real card sends 1-8 fill bytes before its R1.
							// SdFat discards the first byte after a command for exactly
							// this reason, so answering on that byte loses the response.
							this.Buffer[this.BytesToSend++] = 0xff;
							this.Buffer[this.BytesToSend++] = 0;
							this.AppCommand = true;
						}
						break;

						// CMD58 - READ_OCR
					case 0x40 + 58:
						if (this.Index == 6)
						{
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							// Ncr: a real card sends 1-8 fill bytes before its R1.
							// SdFat discards the first byte after a command for exactly
							// this reason, so answering on that byte loses the response.
							this.Buffer[this.BytesToSend++] = 0xff;
							this.Buffer[this.BytesToSend++] = 0;
						}
						break;

					case 0xff:
						this.Index = 0;
						this.Status = 0xff;
						break;

					default:
						if (this.Index == 6)
						{
							// unknown command
							this.Status = 0x04;
							this.Index = 0;
						}
						break;
				}
			}
			else
			{
				switch (this.Received[0])
				{
					// SD_SEND_OP_COND
					case 0x40 + 41:
						if (this.Index == 6)
						{
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							// Ncr: a real card sends 1-8 fill bytes before its R1.
							// SdFat discards the first byte after a command for exactly
							// this reason, so answering on that byte loses the response.
							this.Buffer[this.BytesToSend++] = 0xff;
							this.Buffer[this.BytesToSend++] = 0x00;
							this.AppCommand = false;
						}
						break;

						// ACMD23 - SET_WR_BLK_ERASE_COUNT, a pre-erase hint.
						// Nothing to erase here, but it has to be accepted or
						// SdFat abandons the multi-block write.
					case 0x40 + 23:
						if (this.Index == 6)
						{
							this.Status = 0xff;
							this.Index = 0;
							this.SendIndex = 0;
							this.BytesToSend = 0;
							this.Buffer[this.BytesToSend++] = 0xff;	// Ncr
							this.Buffer[this.BytesToSend++] = 0x00;
							this.AppCommand = false;
						}
						break;

					case 0xff:
						this.Index = 0;
						this.Status = 0xff;
						break;

					default:
						if (this.Index == 6)
						{
							// unknown acmd
							this.Status = 0x04;
							this.Index = 0;
							this.AppCommand = false;
						}
						break;
				}
			}

			SPI.ReceiveByte(this.Status);
		}
	}

});
